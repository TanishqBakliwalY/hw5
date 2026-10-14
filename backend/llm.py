"""The one LLM every agent uses: gpt-6-luna through the Portkey gateway."""

import os
from functools import lru_cache

from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

from .config import MODEL_NAME, MODEL_TIMEOUT_SECONDS, PORTKEY_BASE_URL


class MissingAPIKey(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_model() -> OpenAIResponsesModel:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise MissingAPIKey("PORTKEY_API_KEY is not set. Add it to the .env file (never commit it).")
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        timeout=MODEL_TIMEOUT_SECONDS,  # a hung model call fails the run instead of stalling it
        max_retries=2,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": "openai"},
    )
    # Responses API: gpt-6-luna does not accept function tools with reasoning on /v1/chat/completions.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))
