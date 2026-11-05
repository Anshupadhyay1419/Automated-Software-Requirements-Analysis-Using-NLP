"""Talks to the local Ollama model and checks its answer with Pydantic.

If the model cannot be reached or replies badly, this file raises an error.
It never makes up an answer, so a failure is always visible to the user.
"""
import requests
from pydantic import BaseModel, ValidationError

from .. import config


class LLMUnavailable(Exception):
    """Ollama is not running, or the model is not installed."""


class LLMBadOutput(Exception):
    """Ollama replied, but the reply did not match the expected JSON."""


# The model chosen on the Settings page. Empty means "pick automatically".
selected_model = config.OLLAMA_MODEL

MAX_REPLY_TOKENS = 500  # far more than any valid answer needs


def list_models() -> list[str]:
    try:
        response = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        response.raise_for_status()
    except requests.RequestException as error:
        raise LLMUnavailable(
            f"Cannot reach Ollama at {config.OLLAMA_URL}. "
            "Start it with 'ollama serve', then try again."
        ) from error
    return [model["name"] for model in response.json().get("models", [])]


def choose_model(installed: list[str]) -> str | None:
    """Use the selected model if installed. Otherwise prefer Qwen instruct, then any Qwen."""
    if selected_model in installed:
        return selected_model
    if selected_model:
        return None  # the user asked for a model that is missing, so do not swap silently
    qwen = [name for name in installed if "qwen" in name.lower()]
    instruct = [name for name in qwen if "instruct" in name.lower()]
    return (instruct or qwen or [None])[0]


def active_model() -> str:
    model = choose_model(list_models())
    if model is None:
        wanted = selected_model or "qwen3:4b-instruct-2507-q4_K_M"
        raise LLMUnavailable(f"Model '{wanted}' is not installed. Run: ollama pull {wanted}")
    return model


def ask_llm(system_prompt: str, user_prompt: str, schema: type[BaseModel]) -> BaseModel:
    """Send a prompt, force the reply into the schema's JSON shape, and validate it."""
    body = {
        "model": active_model(),
        "stream": False,
        "think": False,
        "format": schema.model_json_schema(),
        # num_predict limits the reply length, so a model that keeps writing cannot hang the app.
        "options": {"temperature": 0, "seed": 42, "num_predict": MAX_REPLY_TOKENS},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        response = requests.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=config.OLLAMA_TIMEOUT)
        response.raise_for_status()
    except requests.Timeout as error:
        raise LLMUnavailable(
            f"Ollama did not reply within {config.OLLAMA_TIMEOUT} seconds, so it may be stuck. "
            f"Run 'ollama stop {body['model']}' and try again."
        ) from error
    except requests.RequestException as error:
        raise LLMUnavailable(f"The call to Ollama failed: {error}") from error

    try:
        return schema.model_validate_json(response.json()["message"]["content"])
    except (ValidationError, KeyError, ValueError) as error:
        raise LLMBadOutput(f"The model reply was not valid: {error}") from error
