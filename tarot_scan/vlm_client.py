"""vLLM Vision API client."""

import base64
import json
import re
from pathlib import Path

import httpx

from tarot_scan.config import (
    DEFAULT_VLM_MAX_TOKENS,
    DEFAULT_VLM_TEMPERATURE,
    DEFAULT_VLM_TIMEOUT,
    get_vllm_base_url,
    get_vllm_model,
)
from tarot_scan.models import CardClassification


class VLMError(Exception):
    """VLM API error."""

    pass


CLASSIFICATION_PROMPT = '''Identify this tarot card. Analyze the imagery carefully.

Output ONLY valid JSON matching this exact schema (no markdown, no explanation):
{
  "deck_hint": "string or null - deck name if recognizable from art style",
  "card_name": "full card name, e.g. 'Three of Wands' or 'The Fool'",
  "arcana": "major" or "minor",
  "suit": "wands", "cups", "swords", "pentacles", or null for major arcana,
  "rank": "ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "page", "knight", "queen", "king", or null for major arcana,
  "major_number": 0-21 for major arcana (0=Fool, 1=Magician, ..., 21=World), null for minor,
  "orientation": "upright", "reversed", or "unknown",
  "confidence": 0.0 to 1.0,
  "notes": "any additional observations about the card or image quality"
}

Rules:
- For MAJOR arcana: suit and rank must be null, major_number must be 0-21
- For MINOR arcana: major_number must be null, suit and rank must be set
- Output raw JSON only, no markdown code blocks'''


def encode_image(image_path: Path) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_image_mime(image_path: Path) -> str:
    """Get MIME type from extension."""
    ext = image_path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }.get(ext, "image/png")


def list_models(base_url: str | None = None) -> list[str]:
    """List available models from vLLM.

    Args:
        base_url: API base URL (default from env)

    Returns:
        List of model IDs

    Raises:
        VLMError: If API call fails
    """
    base_url = base_url or get_vllm_base_url()

    try:
        response = httpx.get(f"{base_url}/models", timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return [m.get("id") for m in data.get("data", [])]
    except httpx.HTTPError as e:
        raise VLMError(f"Failed to list models: {e}")


def get_model(base_url: str | None = None) -> str:
    """Get model ID to use.

    Args:
        base_url: API base URL

    Returns:
        Model ID from env var or first available model

    Raises:
        VLMError: If no models available
    """
    configured = get_vllm_model()
    if configured:
        return configured

    models = list_models(base_url)
    if not models:
        raise VLMError("No models available from vLLM server")
    return models[0]


def _parse_json_response(content: str) -> dict:
    """Parse JSON from VLM response, handling markdown blocks.

    Args:
        content: Raw response content

    Returns:
        Parsed JSON dict

    Raises:
        ValueError: If JSON parsing fails
    """
    content = content.strip()

    # Handle markdown code blocks
    if "```" in content:
        # Extract content between code blocks
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            content = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in content
    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from response: {content[:200]}")


def classify_image(
    image_path: Path,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float = DEFAULT_VLM_TIMEOUT,
    max_tokens: int = DEFAULT_VLM_MAX_TOKENS,
    temperature: float = DEFAULT_VLM_TEMPERATURE,
    retry_on_parse_error: bool = True,
) -> CardClassification:
    """Classify a tarot card image using VLM.

    Args:
        image_path: Path to card image
        model: Model ID (None = auto-detect)
        base_url: API base URL (None = from env)
        timeout: HTTP timeout in seconds
        max_tokens: Max response tokens
        temperature: Sampling temperature
        retry_on_parse_error: Retry once if JSON parsing fails

    Returns:
        Parsed classification result

    Raises:
        VLMError: If API call fails or response invalid
    """
    base_url = base_url or get_vllm_base_url()
    model = model or get_model(base_url)

    b64_image = encode_image(image_path)
    mime_type = get_image_mime(image_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64_image}"},
                    },
                    {"type": "text", "text": CLASSIFICATION_PROMPT},
                ],
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise VLMError(f"VLM API request failed: {e}")

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    # Parse JSON response
    try:
        parsed = _parse_json_response(content)
    except ValueError as e:
        if retry_on_parse_error:
            # Retry with stricter prompt
            payload["messages"][0]["content"][1]["text"] += (
                "\n\nIMPORTANT: Output ONLY the JSON object, nothing else."
            )
            try:
                response = httpx.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                parsed = _parse_json_response(content)
            except (httpx.HTTPError, ValueError) as e2:
                raise VLMError(f"Failed to get valid JSON after retry: {e2}")
        else:
            raise VLMError(f"JSON parse error: {e}")

    # Validate with Pydantic
    try:
        return CardClassification.model_validate(parsed)
    except Exception as e:
        raise VLMError(f"Invalid classification result: {e}\nRaw: {parsed}")


def health_check(base_url: str | None = None) -> tuple[bool, str]:
    """Check if vLLM server is healthy.

    Args:
        base_url: API base URL

    Returns:
        (healthy, message) tuple
    """
    base_url = base_url or get_vllm_base_url()
    # Remove /v1 suffix for health endpoint
    health_url = base_url.replace("/v1", "") + "/health"

    try:
        response = httpx.get(health_url, timeout=5.0)
        if response.status_code == 200:
            models = list_models(base_url)
            return True, f"Healthy. Models: {', '.join(models)}"
        return False, f"Unhealthy: status {response.status_code}"
    except httpx.HTTPError as e:
        return False, f"Cannot reach server: {e}"
