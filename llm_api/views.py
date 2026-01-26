import json
import os
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

# Provider constants
PROVIDER_OPENAI = "openai"
PROVIDER_DEEPSEEK = "deepseek"

DEEPSEEK_BASE_URL = "https://api.deepseek.com"


def _get_client(provider: str):
    """Return an OpenAI-compatible client for the given provider."""
    if provider == PROVIDER_DEEPSEEK:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    # OpenAI (default)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def call_llm_api(
    prompt,
    model=None,
    response_format=None,
    system_message=None,
    provider=None,
):
    """
    Call an LLM API (OpenAI or DeepSeek) with optional structured response.
    Defaults to OpenAI with model gpt-5-nano.

    Args:
        prompt (str): The prompt/question to send.
        model (str, optional): Model to use. Defaults: "gpt-5-nano" for OpenAI, "deepseek-chat" for DeepSeek.
        response_format (BaseModel, optional): Pydantic model for structured JSON response.
        system_message (str, optional): System message for context.
        provider (str, optional): "openai" or "deepseek". Defaults to LLM_PROVIDER env var or "openai".

    Returns:
        str or BaseModel: Response text or parsed structured data.

    Raises:
        ValueError: If the required API key for the chosen provider is not set.
        Exception: If the API call fails.
    """
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", PROVIDER_OPENAI).lower()
    if provider not in (PROVIDER_OPENAI, PROVIDER_DEEPSEEK):
        raise ValueError(f"provider must be '{PROVIDER_OPENAI}' or '{PROVIDER_DEEPSEEK}', got: {provider}")

    if model is None:
        model = "deepseek-chat" if provider == PROVIDER_DEEPSEEK else "gpt-5-nano"

    try:
        client = _get_client(provider)

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        api_params = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        if response_format:
            if provider == PROVIDER_OPENAI:
                api_params["response_format"] = response_format
                response = client.chat.completions.parse(**api_params)
                return response.choices[0].message.parsed
            else:
                # DeepSeek: use JSON mode and parse manually
                api_params["response_format"] = {"type": "json_object"}
                response = client.chat.completions.create(**api_params)
                content = response.choices[0].message.content
                data = json.loads(content)
                return response_format.model_validate(data)
        else:
            response = client.chat.completions.create(**api_params)
            return response.choices[0].message.content

    except Exception as e:
        raise Exception(f"Failed to call {provider} API: {str(e)}")


# Create your views here.
