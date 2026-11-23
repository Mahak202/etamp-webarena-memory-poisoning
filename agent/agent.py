from etamp.inject import clean_turns, poisoned_turns, poisoned_turns_reverse, poisoned_turns_helpful, poisoned_turns_consensus, poisoned_turns_reciprocity, poisoned_turns_fear, poisoned_turns_trust, poisoned_turns_fatigue, poisoned_turns_scarcity
from etamp.real_turns import real_turns_from_render
import argparse
import json
from typing import Any

import tiktoken
from beartype import beartype

from agent.prompts import *
from browser_env import Trajectory
from browser_env.actions import (
    Action,
    ActionParsingError,
    create_id_based_action,
    create_none_action,
    create_playwright_action,
)
from browser_env.utils import Observation, StateInfo
from llms import (
    call_llm,
    generate_from_huggingface_completion,
    generate_from_openai_chat_completion,
    generate_from_openai_completion,
    lm_config,
)
from llms.tokenizers import Tokenizer


class Agent:
    """Base class for the agent"""

    def __init__(self, *args: Any) -> None:
        pass

    def next_action(
        self, trajectory: Trajectory, intent: str, meta_data: Any
    ) -> Action:
        """Predict the next action given the observation"""
        raise NotImplementedError

    def reset(
        self,
        test_config_file: str,
    ) -> None:
        raise NotImplementedError


class TeacherForcingAgent(Agent):
    """Agent that follows a pre-defined action sequence"""

    def __init__(self) -> None:
        super().__init__()

    def set_action_set_tag(self, tag: str) -> None:
        self.action_set_tag = tag

    def set_actions(self, action_seq: str | list[str]) -> None:
        if isinstance(action_seq, str):
            action_strs = action_seq.strip().split("\n")
        else:
            action_strs = action_seq
        action_strs = [a.strip() for a in action_strs]

        actions = []
        for a_str in action_strs:
            try:
                if self.action_set_tag == "playwright":
                    cur_action = create_playwright_action(a_str)
                elif self.action_set_tag == "id_accessibility_tree":
                    cur_action = create_id_based_action(a_str)
                else:
                    raise ValueError(
                        f"Unknown action type {self.action_set_tag}"
                    )
            except ActionParsingError as e:
                cur_action = create_none_action()

            cur_action["raw_prediction"] = a_str
            actions.append(cur_action)

        self.actions: list[Action] = actions

    def next_action(
        self, trajectory: Trajectory, intent: str, meta_data: Any
    ) -> Action:
        """Predict the next action given the observation"""
        return self.actions.pop(0)

    def reset(
        self,
        test_config_file: str,
    ) -> None:
        with open(test_config_file) as f:
            ref_actions = json.load(f)["reference_action_sequence"]
            tag = ref_actions["action_set_tag"]
            action_seq = ref_actions["action_sequence"]
            self.set_action_set_tag(tag)
            self.set_actions(action_seq)


class PromptAgent(Agent):
    """prompt-based agent that emits action given the history"""

    @beartype
    def __init__(
        self,
        action_set_tag: str,
        lm_config: lm_config.LMConfig,
        prompt_constructor: PromptConstructor,
    ) -> None:
        super().__init__()
        self.lm_config = lm_config
        self.prompt_constructor = prompt_constructor
        self.action_set_tag = action_set_tag

    def set_action_set_tag(self, tag: str) -> None:
        self.action_set_tag = tag

    @beartype
    def next_action(
        self, trajectory: Trajectory, intent: str, meta_data: dict[str, Any]
    ) -> Action:
        prompt = self.prompt_constructor.construct(
            trajectory, intent, meta_data
        )
        poison_pid = getattr(getattr(self, "args", None), "poison_pid", None)
        if hasattr(self, "args") and getattr(self.args, "poison_pid", None):
            poison_pid = self.args.poison_pid
        matched_clean = bool(getattr(getattr(self, "args", None), "matched_clean", False))

        poison_direction = getattr(getattr(self, "args", None), "poison_direction", "shop2reddit")
        poison_style = getattr(getattr(self, "args", None), "poison_style", "urgency_override")

        print(f"[DEBUG] Checking poison_pid: {poison_pid} matched_clean: {matched_clean} direction: {poison_direction} style: {poison_style}")
        if poison_pid:
            if poison_direction == "reddit2shop":
                p_turns = poisoned_turns_reverse("Browse reddit post", "Sample Post", poison_pid)
            elif poison_style == "helpfulness":
                p_turns = poisoned_turns_helpful("Shop product", "Sample Item", poison_pid)
            elif poison_style == "consensus":
                p_turns = poisoned_turns_consensus("Shop product", "Sample Item", poison_pid)
            elif poison_style == "reciprocity":
                p_turns = poisoned_turns_reciprocity("Shop product", "Sample Item", poison_pid)
            elif poison_style == "fear":
                p_turns = poisoned_turns_fear("Shop product", "Sample Item", poison_pid)
            elif poison_style == "trust":
                p_turns = poisoned_turns_trust("Shop product", "Sample Item", poison_pid)
            elif poison_style == "fatigue":
                p_turns = poisoned_turns_fatigue("Shop product", "Sample Item", poison_pid)
            elif poison_style == "scarcity":
                p_turns = poisoned_turns_scarcity("Shop product", "Sample Item", poison_pid)
            else:
                p_turns = poisoned_turns("Shop product", "Sample Item", poison_pid)
            if isinstance(prompt, list):
                prompt = prompt[:1] + p_turns + prompt[1:]
            elif isinstance(prompt, dict) and "messages" in prompt:
                prompt["messages"] = prompt["messages"][:1] + p_turns + prompt["messages"][1:]
            print("[DEBUG] Successfully injected poisoned turns into prompt!")
        elif matched_clean:
            c_turns = clean_turns("Shop product", "Sample Item", 2026)
            if isinstance(prompt, list):
                prompt = prompt[:1] + c_turns + prompt[1:]
            elif isinstance(prompt, dict) and "messages" in prompt:
                prompt["messages"] = prompt["messages"][:1] + c_turns + prompt["messages"][1:]
            print("[DEBUG] Successfully injected matched-clean turns into prompt!")
        lm_config = self.lm_config
        n = 0
        while True:
            response = call_llm(lm_config, prompt)
            force_prefix = self.prompt_constructor.instruction[
                "meta_data"
            ].get("force_prefix", "")
            response = f"{force_prefix}{response}"
            n += 1
            try:
                parsed_response = self.prompt_constructor.extract_action(
                    response
                )
                if self.action_set_tag == "id_accessibility_tree":
                    action = create_id_based_action(parsed_response)
                elif self.action_set_tag == "playwright":
                    action = create_playwright_action(parsed_response)
                else:
                    raise ValueError(
                        f"Unknown action type {self.action_set_tag}"
                    )
                action["raw_prediction"] = response
                break
            except ActionParsingError as e:
                if n >= lm_config.gen_config["max_retry"]:
                    action = create_none_action()
                    action["raw_prediction"] = response
                    break

        return action

    def reset(self, test_config_file: str) -> None:
        pass


def construct_agent(args: argparse.Namespace) -> Agent:
    llm_config = lm_config.construct_llm_config(args)

    agent: Agent
    if args.agent_type == "teacher_forcing":
        agent = TeacherForcingAgent()
    elif args.agent_type == "prompt":
        with open(args.instruction_path) as f:
            constructor_type = json.load(f)["meta_data"]["prompt_constructor"]
        tokenizer = Tokenizer(args.provider, args.model)
        prompt_constructor = eval(constructor_type)(
            args.instruction_path, lm_config=llm_config, tokenizer=tokenizer
        )
        agent = PromptAgent(

            action_set_tag=args.action_set_tag,
            lm_config=llm_config,
            prompt_constructor=prompt_constructor,
        )
    else:
        raise NotImplementedError(
            f"agent type {args.agent_type} not implemented"
        )
    agent.args = args
    return agent
