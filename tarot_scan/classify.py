"""Classification orchestration for tarot card crops."""

from datetime import datetime
from pathlib import Path

from PIL import Image

from tarot_scan.config import DEFAULT_TARGET_HEIGHT, get_vllm_base_url
from tarot_scan.manifest import append_record, get_pending_crops
from tarot_scan.models import CardCropMeta, ClassRecord
from tarot_scan.vlm_client import VLMError, classify_image, get_model


def resize_for_vlm(image_path: Path, target_height: int, output_path: Path) -> Path:
    """Resize image to target height for faster VLM processing.

    Args:
        image_path: Source image path
        target_height: Target height in pixels
        output_path: Where to save resized image

    Returns:
        Path to resized image (may be same as input if no resize needed)
    """
    with Image.open(image_path) as img:
        if img.height <= target_height:
            return image_path

        # Calculate new dimensions preserving aspect ratio
        ratio = target_height / img.height
        new_width = int(img.width * ratio)

        resized = img.resize((new_width, target_height), Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resized.save(output_path, "PNG")
        return output_path


def classify_crops(
    deck_dir: Path,
    pending_only: bool = True,
    max_cards: int | None = None,
    resize_height: int | None = DEFAULT_TARGET_HEIGHT,
    model: str | None = None,
    progress_callback=None,
) -> list[ClassRecord]:
    """Classify card crops in a deck directory.

    Args:
        deck_dir: Deck directory containing manifest.jsonl
        pending_only: Only process unclassified crops
        max_cards: Maximum number of cards to process
        resize_height: Resize images to this height before VLM (None = no resize)
        model: VLM model ID (None = auto-detect)
        progress_callback: Optional callback(status_msg)

    Returns:
        List of classification records created
    """
    manifest_path = deck_dir / "manifest.jsonl"

    if not manifest_path.exists():
        raise ValueError(f"No manifest found at {manifest_path}")

    # Get crops to process
    if pending_only:
        crops = get_pending_crops(manifest_path)
    else:
        from tarot_scan.manifest import get_crops
        crops = get_crops(manifest_path)

    if max_cards:
        crops = crops[:max_cards]

    if not crops:
        if progress_callback:
            progress_callback("No crops to classify")
        return []

    if progress_callback:
        progress_callback(f"Classifying {len(crops)} cards...")

    # Get model
    base_url = get_vllm_base_url()
    if model is None:
        model = get_model(base_url)

    if progress_callback:
        progress_callback(f"Using model: {model}")

    # Temp directory for resized images
    temp_dir = deck_dir / ".temp"

    results = []
    for i, crop in enumerate(crops):
        if progress_callback:
            progress_callback(f"Classifying {i + 1}/{len(crops)}: {crop.crop_id}")

        # Get full path to crop
        crop_path = deck_dir / crop.file

        if not crop_path.exists():
            if progress_callback:
                progress_callback(f"Warning: Crop not found: {crop_path}")
            continue

        # Resize if needed
        if resize_height:
            resized_path = temp_dir / f"{crop.crop_id}_resized.png"
            image_path = resize_for_vlm(crop_path, resize_height, resized_path)
        else:
            image_path = crop_path

        # Classify
        try:
            classification = classify_image(image_path, model=model, base_url=base_url)

            # Create record
            record = ClassRecord(
                crop_id=crop.crop_id,
                model=model,
                timestamp=datetime.now(),
                result=classification,
            )

            # Append to manifest
            append_record(manifest_path, record)
            results.append(record)

            if progress_callback:
                progress_callback(
                    f"  -> {classification.card_name} ({classification.confidence:.0%})"
                )

        except VLMError as e:
            if progress_callback:
                progress_callback(f"  -> Error: {e}")
            continue

    # Cleanup temp files
    if temp_dir.exists():
        for f in temp_dir.iterdir():
            f.unlink()
        temp_dir.rmdir()

    if progress_callback:
        progress_callback(f"Classified {len(results)}/{len(crops)} cards")

    return results


def classify_single(
    image_path: Path,
    model: str | None = None,
    resize_height: int | None = DEFAULT_TARGET_HEIGHT,
    progress_callback=None,
) -> ClassRecord | None:
    """Classify a single image file.

    Args:
        image_path: Path to image
        model: VLM model ID
        resize_height: Resize to this height
        progress_callback: Optional callback

    Returns:
        Classification record or None on error
    """
    if not image_path.exists():
        raise ValueError(f"Image not found: {image_path}")

    base_url = get_vllm_base_url()
    if model is None:
        model = get_model(base_url)

    # Resize if needed
    if resize_height:
        temp_path = image_path.parent / f".temp_{image_path.stem}.png"
        image_to_classify = resize_for_vlm(image_path, resize_height, temp_path)
        cleanup_temp = image_to_classify != image_path
    else:
        image_to_classify = image_path
        cleanup_temp = False

    try:
        if progress_callback:
            progress_callback(f"Classifying {image_path.name}...")

        classification = classify_image(image_to_classify, model=model, base_url=base_url)

        record = ClassRecord(
            crop_id=image_path.stem,
            model=model,
            timestamp=datetime.now(),
            result=classification,
        )

        if progress_callback:
            progress_callback(f"Result: {classification.card_name}")

        return record

    except VLMError as e:
        if progress_callback:
            progress_callback(f"Error: {e}")
        return None

    finally:
        if cleanup_temp and temp_path.exists():
            temp_path.unlink()
