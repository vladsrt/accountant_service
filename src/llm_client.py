from __future__ import annotations

import json
import time

from openai import OpenAI, RateLimitError

from src.config import (
    OPENAI_API_KEY,
    FRONT_DESK_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
)


_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


def call_llm(
    system_prompt: str,
    user_message: str,
    schema: dict,
    model: str = FRONT_DESK_MODEL,
    temperature: float = LLM_TEMPERATURE,
) -> tuple[dict, dict]:
    """
    Generic LLM call with structured output.
    Handles 429 rate limit errors with exponential backoff.
    Returns (parsed_data_dict, metadata_dict).
    """
    client = get_client()
    metadata = {"model": model, "tokens": 0, "latency_ms": 0}
    max_attempts = LLM_MAX_RETRIES + 5  # extra retries for rate limits

    for attempt in range(max_attempts):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": schema,
                },
            )
            elapsed_ms = int((time.time() - start) * 1000)

            content = response.choices[0].message.content
            data = json.loads(content)

            metadata["tokens"] = response.usage.total_tokens if response.usage else 0
            metadata["latency_ms"] = elapsed_ms

            return data, metadata

        except RateLimitError:
            wait = min(2**attempt, 30)  # exponential backoff, max 30s
            time.sleep(wait)

        except Exception as e:
            if attempt < max_attempts - 1:
                time.sleep(min(2**attempt, 10))
            else:
                raise RuntimeError(f"LLM call failed after {max_attempts} retries: {e}")
