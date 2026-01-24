"""Configuration from environment variables and defaults."""

import os
from pathlib import Path


def get_vllm_base_url() -> str:
    """Get vLLM API base URL."""
    return os.environ.get("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")


def get_vllm_model() -> str | None:
    """Get vLLM model ID (None = auto-detect from /v1/models)."""
    return os.environ.get("VLLM_MODEL")


def get_sane_device() -> str | None:
    """Get SANE device string (None = auto-detect)."""
    return os.environ.get("SANE_DEVICE")


def get_decks_dir() -> Path:
    """Get base directory for deck storage."""
    return Path(os.environ.get("TAROT_DECKS_DIR", "./decks"))


# Default scanning parameters
DEFAULT_DPI = 600
DEFAULT_SCAN_MODE = "Color"
DEFAULT_SCAN_FORMAT = "png"

# Detection parameters
DEFAULT_MIN_AREA_FRAC = 0.01  # Min card area as fraction of image
DEFAULT_MAX_AREA_FRAC = 0.5  # Max card area as fraction of image
DEFAULT_EPSILON_FRAC = 0.02  # Contour approximation epsilon factor
DEFAULT_TARGET_HEIGHT = 1024  # Resize crops to this height for VLM

# VLM parameters
DEFAULT_VLM_TIMEOUT = 60.0  # HTTP timeout in seconds
DEFAULT_VLM_MAX_TOKENS = 500
DEFAULT_VLM_TEMPERATURE = 0.1
