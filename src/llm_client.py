from __future__ import annotations

import asyncio
import json
import time

from openai import AsyncOpenAI, RateLimitError

from app.core.config import settings

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def call_llm(
    system_prompt: str,
    user_message: str,
    schema: dict,
    model: str = settings.FRONT_DESK_MODEL,
    temperature: float = settings.LLM_TEMPERATURE,
) -> tuple[dict, dict]:
    """
    Async LLM call with structured output.
    Handles 429 rate limit errors with exponential backoff.
    Returns (parsed_data_dict, metadata_dict).
    """
    client = get_client()
    metadata = {"model": model, "tokens": 0, "latency_ms": 0}
    max_attempts = settings.LLM_MAX_RETRIES + 5  # extra retries for rate limits

    for attempt in range(max_attempts):
        try:
            start = time.time()
            response = await client.chat.completions.create(
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
            await asyncio.sleep(wait)

        except Exception as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(min(2**attempt, 10))
            else:
                raise RuntimeError(f"LLM call failed after {max_attempts} retries: {e}")

    raise RuntimeError(f"LLM call failed after {max_attempts} retries: rate limited")
