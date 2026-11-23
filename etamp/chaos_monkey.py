import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import random


def _caesar(text: str, shift: int = 3) -> str:
    out = []
    for ch in text:
        if ch.isalpha():
            base = ord('A') if ch.isupper() else ord('a')
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def maybe_drop_click(action, p_click):
    from browser_env.actions import ActionTypes
    if action["action_type"] in (ActionTypes.CLICK, ActionTypes.MOUSE_CLICK):
        if random.random() < p_click:
            action = dict(action)
            action["action_type"] = ActionTypes.NONE  # silently no-op
    return action


def maybe_swap_scroll(action, p_scroll):
    from browser_env.actions import ActionTypes
    if action["action_type"] == ActionTypes.SCROLL:
        if random.random() < p_scroll:
            action = dict(action)
            action["direction"] = "up" if action["direction"] == "down" else "down"
    return action


def maybe_garble_type(action, p_type):
    from browser_env.actions import ActionTypes, _id2key, _keys2ids
    if action["action_type"] == ActionTypes.TYPE:
        if random.random() < p_type:
            action = dict(action)
            ids = action.get("text", [])
            # decode ids -> characters, using _id2key as the inverse lookup table
            chars = "".join(
                _id2key[i] if 0 <= i < len(_id2key) else ""
                for i in ids
            )
            shifted = _caesar(chars)
            action["text"] = _keys2ids(shifted)
    return action


def apply_chaos(action, enabled=False, p_click=0.4, p_scroll=1.0, p_type=1.0):
    if not enabled:
        return action
    action = maybe_drop_click(action, p_click)
    action = maybe_swap_scroll(action, p_scroll)
    action = maybe_garble_type(action, p_type)
    return action
