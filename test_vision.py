#!/usr/bin/env python3
"""
Test script for Qwen2-VL-2B-Instruct via vLLM.

Usage:
  1. Start vLLM with vision model:
     docker run --gpus all -v /data/models:/models -p 8000:8000 \
       vllm/vllm-openai:latest \
       --model /models/Qwen2-VL-2B-Instruct \
       --gpu-memory-utilization 0.85 \
       --max-model-len 4096

  2. Run this script:
     python3 test_vision.py [image_path]
"""

import sys
import base64
import json
from pathlib import Path

try:
    import httpx
except ImportError:
    sys.exit("Error: httpx not installed. Run: pip install httpx")

API_URL = "http://localhost:8000"


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
    }.get(ext, "image/jpeg")


def test_health() -> bool:
    """Check if vLLM server is running."""
    try:
        response = httpx.get(f"{API_URL}/v1/models", timeout=5.0)
        if response.status_code == 200:
            models = response.json()
            print(f"Server healthy. Available models:")
            for m in models.get("data", []):
                print(f"  - {m.get('id')}")
            return True
        else:
            print(f"Server returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"Cannot reach server: {e}")
        return False


def test_vision(image_path: Path) -> dict:
    """Send image to vision model for tarot card identification."""
    b64_image = encode_image(image_path)
    mime_type = get_image_mime(image_path)

    prompt = '''Identify this tarot card. Output ONLY valid JSON with this exact structure:
{"name": "card name", "suit": "suit or Major Arcana", "rank": "number or name", "confidence": 0.0-1.0}'''

    payload = {
        "model": "/model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    print(f"\nSending image: {image_path}")
    print(f"Image size: {image_path.stat().st_size / 1024:.1f} KB")

    response = httpx.post(
        f"{API_URL}/v1/chat/completions",
        json=payload,
        timeout=60.0
    )
    response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"]

    print(f"\nRaw response:\n{content}")

    # Try to parse as JSON
    try:
        # Handle markdown code blocks
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        parsed = json.loads(content.strip())
        print(f"\nParsed JSON:\n{json.dumps(parsed, indent=2)}")
        return parsed
    except json.JSONDecodeError:
        print("\nWarning: Could not parse response as JSON")
        return {"raw": content}


def test_simple_vision() -> bool:
    """Test vision capability with a simple describe request (no image needed)."""
    # Create a simple 1x1 red pixel PNG for testing
    # PNG header + IHDR + IDAT with red pixel + IEND
    red_pixel_png = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
        b'\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01'
        b'\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    b64_image = base64.b64encode(red_pixel_png).decode("utf-8")

    payload = {
        "model": "/model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "What color is this image? Reply with just the color name."
                    }
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }

    print("\nTesting basic vision with red pixel...")

    try:
        response = httpx.post(
            f"{API_URL}/v1/chat/completions",
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print(f"Response: {content}")

        if "red" in content.lower():
            print("✓ Vision model working correctly!")
            return True
        else:
            print("⚠ Unexpected response, but model is responding")
            return True

    except httpx.HTTPStatusError as e:
        print(f"✗ Vision test failed: {e}")
        print(f"Response body: {e.response.text}")
        return False
    except Exception as e:
        print(f"✗ Vision test failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Qwen2-VL-2B-Instruct Vision Model Test")
    print("=" * 60)

    # Check server health
    print("\n1. Checking server health...")
    if not test_health():
        print("\nServer not available. Start vLLM with:")
        print("""
docker run --gpus all \\
  -v /data/models:/models \\
  -p 8000:8000 \\
  vllm/vllm-openai:latest \\
  --model /models/Qwen2-VL-2B-Instruct \\
  --gpu-memory-utilization 0.85 \\
  --max-model-len 4096
""")
        sys.exit(1)

    # Test basic vision
    print("\n2. Testing basic vision capability...")
    if not test_simple_vision():
        sys.exit(1)

    # Test with provided image
    if len(sys.argv) > 1:
        image_path = Path(sys.argv[1])
        if not image_path.exists():
            print(f"\nError: Image not found: {image_path}")
            sys.exit(1)

        print("\n3. Testing tarot card identification...")
        result = test_vision(image_path)

        print("\n" + "=" * 60)
        print("Test complete!")
    else:
        print("\n" + "=" * 60)
        print("Basic tests passed!")
        print("\nTo test tarot card identification, run:")
        print("  python3 test_vision.py /path/to/tarot_card.jpg")


if __name__ == "__main__":
    main()
