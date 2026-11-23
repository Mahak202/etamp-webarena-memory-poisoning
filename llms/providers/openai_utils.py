"""Tools to generate from OpenAI prompts.
Adopted from https://github.com/zeno-ml/zeno-build/"""

import asyncio
import logging
import os
import random
import time
from typing import Any

import aiolimiter
import openai
import tiktoken
from openai import AsyncOpenAI, OpenAI
from tqdm.asyncio import tqdm_asyncio

from etamp.budget import commit as budget_commit
from etamp.budget import reserve as budget_reserve

RETRYABLE_ERRORS = (openai.RateLimitError, openai.APITimeoutError)


def retry_with_exponential_backoff(  # type: ignore
    func,
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    errors: tuple[Any] = RETRYABLE_ERRORS,
):
    """Retry a function with exponential backoff."""

    def wrapper(*args, **kwargs):  # type: ignore
        num_retries = 0
        delay = initial_delay

        while True:
            try:
                return func(*args, **kwargs)
            except errors as e:
                num_retries += 1
                if num_retries > max_retries:
                    raise Exception(
                        f"Maximum number of retries ({max_retries}) exceeded."
                    )
                delay *= exponential_base * (1 + jitter * random.random())
                print(f"Retrying in {delay} seconds.")
                time.sleep(delay)
            except Exception as e:
                raise e

    return wrapper


def _client() -> OpenAI:
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError(
            "OPENAI_API_KEY environment variable must be set when using OpenAI API."
        )
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        organization=os.environ.get("OPENAI_ORGANIZATION", "") or None,
    )


def _async_client() -> AsyncOpenAI:
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError(
            "OPENAI_API_KEY environment variable must be set when using OpenAI API."
        )
    return AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        organization=os.environ.get("OPENAI_ORGANIZATION", "") or None,
    )


def _count_tokens(model: str, messages: list[dict[str, str]]) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return sum(len(enc.encode(m.get("content", ""))) for m in messages) + 8 * len(
        messages
    )


async def _throttled_openai_completion_acreate(
    engine: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    limiter: aiolimiter.AsyncLimiter,
) -> dict[str, Any]:
    client = _async_client()
    async with limiter:
        for _ in range(3):
            try:
                r = await client.completions.create(
                    model=engine,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                )
                return {"choices": [{"message": {"content": r.choices[0].text}}]}
            except openai.RateLimitError:
                logging.warning(
                    "OpenAI API rate limit exceeded. Sleeping for 10 seconds."
                )
                await asyncio.sleep(10)
            except openai.APIError as e:
                logging.warning(f"OpenAI API error: {e}")
                break
        return {"choices": [{"message": {"content": ""}}]}


async def agenerate_from_openai_completion(
    prompts: list[str],
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    requests_per_minute: int = 300,
) -> list[str]:
    limiter = aiolimiter.AsyncLimiter(requests_per_minute)
    async_responses = [
        _throttled_openai_completion_acreate(
            engine=engine,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            limiter=limiter,
        )
        for prompt in prompts
    ]
    responses = await tqdm_asyncio.gather(*async_responses)
    return [x["choices"][0]["message"]["content"] for x in responses]


@retry_with_exponential_backoff
def generate_from_openai_completion(
    prompt: str,
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    client = _client()
    response = client.completions.create(
        model=engine,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stop=[stop_token] if stop_token else None,
    )
    return response.choices[0].text


async def _throttled_openai_chat_completion_acreate(
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float,
    limiter: aiolimiter.AsyncLimiter,
) -> dict[str, Any]:
    client = _async_client()
    async with limiter:
        for _ in range(3):
            try:
                r = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=top_p,
                )
                return {"choices": [{"message": {"content": r.choices[0].message.content}}]}
            except openai.RateLimitError:
                logging.warning(
                    "OpenAI API rate limit exceeded. Sleeping for 10 seconds."
                )
                await asyncio.sleep(10)
            except asyncio.exceptions.TimeoutError:
                logging.warning("OpenAI API timeout. Sleeping for 10 seconds.")
                await asyncio.sleep(10)
            except openai.APIError as e:
                logging.warning(f"OpenAI API error: {e}")
                break
        return {"choices": [{"message": {"content": ""}}]}


async def agenerate_from_openai_chat_completion(
    messages_list: list[list[dict[str, str]]],
    engine: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    requests_per_minute: int = 300,
) -> list[str]:
    limiter = aiolimiter.AsyncLimiter(requests_per_minute)
    async_responses = [
        _throttled_openai_chat_completion_acreate(
            model=engine,
            messages=message,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            limiter=limiter,
        )
        for message in messages_list
    ]
    responses = await tqdm_asyncio.gather(*async_responses)
    return [x["choices"][0]["message"]["content"] for x in responses]


@retry_with_exponential_backoff
def generate_from_openai_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    top_p: float,
    context_length: int,
    max_tokens: int,
    stop_token: str | None = None,
) -> str:
    client = _client()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stop=[stop_token] if stop_token else None,
    )
    return response.choices[0].message.content or ""


def generate_from_openai_responses(
    messages: list[dict[str, str]],
    model: str,
    reasoning_effort: str,
    max_output_tokens: int,
    api_timeout: float,
    no_retry: bool,
) -> str:
    """gpt-5.6-luna-style path: Responses API, reasoning.effort control,
    code-enforced token/budget caps (guide sections 2-3). No decorator-based
    retry here — `no_retry` maps straight to the client's max_retries so the
    guide's 'disable automatic API retries' is an actual SDK setting, not a
    convention."""
    input_tokens = _count_tokens(model, messages)
    reservation_id = budget_reserve(input_tokens, max_output_tokens)

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        organization=os.environ.get("OPENAI_ORGANIZATION", "") or None,
        timeout=api_timeout,
        max_retries=0 if no_retry else 2,
    )
    try:
        response = client.responses.create(
            model=model,
            input=messages,
            reasoning={"effort": reasoning_effort},
            max_output_tokens=max_output_tokens,
        )
    except Exception:
        # guide: retain the reservation after a timeout/error rather than
        # dropping it — commit() is simply not called, so the worst-case
        # reservation from budget_reserve() stands as spend.
        raise

    usage = response.usage
    budget_commit(
        reservation_id,
        actual_input_tokens=usage.input_tokens,
        actual_output_tokens=usage.output_tokens,
    )
    return response.output_text or ""


@retry_with_exponential_backoff
# debug only
def fake_generate_from_openai_chat_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    top_p: float,
    context_length: int,
    stop_token: str | None = None,
) -> str:
    if "OPENAI_API_KEY" not in os.environ:
        raise ValueError(
            "OPENAI_API_KEY environment variable must be set when using OpenAI API."
        )
    answer = "Let's think step-by-step. This page shows a list of links and buttons. There is a search box with the label 'Search query'. I will click on the search box to type the query. So the action I will perform is \"click [60]\"."
    return answer
