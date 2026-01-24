"""OpenCV-based tarot card detection and extraction."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tarot_scan.config import (
    DEFAULT_EPSILON_FRAC,
    DEFAULT_MAX_AREA_FRAC,
    DEFAULT_MIN_AREA_FRAC,
    DEFAULT_TARGET_HEIGHT,
)
from tarot_scan.manifest import append_record, get_next_crop_id
from tarot_scan.models import CardCropMeta


@dataclass
class DetectedCard:
    """Intermediate detection result before saving."""

    contour: np.ndarray
    corners: np.ndarray  # 4 corners ordered: TL, TR, BR, BL
    bbox: tuple[int, int, int, int]  # x, y, w, h
    area: float
    center: tuple[float, float]


def order_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 corners as: top-left, top-right, bottom-right, bottom-left.

    Args:
        pts: Array of 4 points

    Returns:
        Ordered array of 4 points
    """
    # Sort by sum (x+y) to get TL and BR
    s = pts.sum(axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]

    # Sort by diff (y-x) to get TR and BL
    d = np.diff(pts, axis=1).flatten()
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]

    return np.array([tl, tr, br, bl], dtype=np.float32)


def perspective_transform(image: np.ndarray, corners: np.ndarray, target_height: int) -> np.ndarray:
    """Apply perspective transform to extract and rectify a card.

    Args:
        image: Source image
        corners: 4 corners (TL, TR, BR, BL)
        target_height: Target height for output

    Returns:
        Rectified card image
    """
    # Calculate card dimensions from corners
    width_top = np.linalg.norm(corners[1] - corners[0])
    width_bottom = np.linalg.norm(corners[2] - corners[3])
    height_left = np.linalg.norm(corners[3] - corners[0])
    height_right = np.linalg.norm(corners[2] - corners[1])

    # Use average dimensions
    card_width = int((width_top + width_bottom) / 2)
    card_height = int((height_left + height_right) / 2)

    # Scale to target height while preserving aspect ratio
    if target_height:
        scale = target_height / card_height
        card_width = int(card_width * scale)
        card_height = target_height

    # Destination points
    dst = np.array(
        [[0, 0], [card_width - 1, 0], [card_width - 1, card_height - 1], [0, card_height - 1]],
        dtype=np.float32,
    )

    # Compute transform and apply
    matrix = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(image, matrix, (card_width, card_height))

    return warped


def detect_cards_in_image(
    image: np.ndarray,
    min_area_frac: float = DEFAULT_MIN_AREA_FRAC,
    max_area_frac: float = DEFAULT_MAX_AREA_FRAC,
    epsilon_frac: float = DEFAULT_EPSILON_FRAC,
) -> list[DetectedCard]:
    """Detect card-like quadrilaterals in an image.

    Args:
        image: Input image (BGR or grayscale)
        min_area_frac: Minimum card area as fraction of image area
        max_area_frac: Maximum card area as fraction of image area
        epsilon_frac: Contour approximation epsilon as fraction of perimeter

    Returns:
        List of detected cards sorted in reading order (top-to-bottom, left-to-right)
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    image_area = gray.shape[0] * gray.shape[1]
    min_area = image_area * min_area_frac
    max_area = image_area * max_area_frac

    # Preprocessing: bilateral filter preserves edges while reducing noise
    blurred = cv2.bilateralFilter(gray, 11, 75, 75)

    # Edge detection
    edges = cv2.Canny(blurred, 30, 100)

    # Dilate edges to close gaps
    kernel = np.ones((3, 3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected = []
    for contour in contours:
        area = cv2.contourArea(contour)

        # Filter by area
        if area < min_area or area > max_area:
            continue

        # Approximate to polygon
        perimeter = cv2.arcLength(contour, True)
        epsilon = epsilon_frac * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Must be quadrilateral
        if len(approx) != 4:
            continue

        # Check if convex
        if not cv2.isContourConvex(approx):
            continue

        # Get ordered corners
        corners = order_corners(approx.reshape(4, 2))

        # Get bounding box
        x, y, w, h = cv2.boundingRect(approx)

        # Check aspect ratio (tarot cards are roughly 2.75" x 4.75", ratio ~1.7)
        aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 0
        if aspect < 1.2 or aspect > 2.5:  # Allow some tolerance
            continue

        center = (x + w / 2, y + h / 2)
        detected.append(
            DetectedCard(
                contour=approx,
                corners=corners,
                bbox=(x, y, w, h),
                area=area,
                center=center,
            )
        )

    # Sort in reading order: top-to-bottom, then left-to-right
    # Group by rough rows (within 10% of image height)
    row_threshold = gray.shape[0] * 0.1
    detected.sort(key=lambda c: c.center[1])  # Sort by Y first

    # Group into rows
    rows = []
    current_row = []
    last_y = None
    for card in detected:
        if last_y is None or card.center[1] - last_y < row_threshold:
            current_row.append(card)
        else:
            if current_row:
                rows.append(sorted(current_row, key=lambda c: c.center[0]))
            current_row = [card]
        last_y = card.center[1]
    if current_row:
        rows.append(sorted(current_row, key=lambda c: c.center[0]))

    # Flatten
    return [card for row in rows for card in row]


def draw_debug_image(
    image: np.ndarray,
    detected: list[DetectedCard],
    output_path: Path,
) -> None:
    """Draw detected cards on image for debugging.

    Args:
        image: Original image
        detected: List of detected cards
        output_path: Path to save annotated image
    """
    debug_img = image.copy()

    for i, card in enumerate(detected):
        # Draw contour
        cv2.drawContours(debug_img, [card.contour], -1, (0, 255, 0), 3)

        # Draw corners
        for j, corner in enumerate(card.corners):
            cv2.circle(debug_img, tuple(corner.astype(int)), 10, (0, 0, 255), -1)
            cv2.putText(
                debug_img,
                str(j),
                tuple(corner.astype(int) + [5, 5]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )

        # Draw label
        cx, cy = int(card.center[0]), int(card.center[1])
        cv2.putText(
            debug_img,
            f"Card {i + 1}",
            (cx - 40, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 0, 0),
            2,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), debug_img)


def detect_and_extract(
    scan_path: Path,
    deck_dir: Path,
    scan_id: str,
    min_area_frac: float = DEFAULT_MIN_AREA_FRAC,
    max_area_frac: float = DEFAULT_MAX_AREA_FRAC,
    epsilon_frac: float = DEFAULT_EPSILON_FRAC,
    target_height: int = DEFAULT_TARGET_HEIGHT,
    debug: bool = False,
    progress_callback=None,
) -> list[CardCropMeta]:
    """Detect cards in a scan and extract crops.

    Args:
        scan_path: Path to scan image
        deck_dir: Deck directory for output
        scan_id: Source scan ID
        min_area_frac: Minimum card area fraction
        max_area_frac: Maximum card area fraction
        epsilon_frac: Contour approximation epsilon fraction
        target_height: Resize crops to this height
        debug: Save debug annotated image
        progress_callback: Optional callback(status_msg)

    Returns:
        List of CardCropMeta for extracted cards
    """
    if progress_callback:
        progress_callback(f"Loading scan: {scan_path.name}")

    # Load image
    image = cv2.imread(str(scan_path))
    if image is None:
        raise ValueError(f"Could not load image: {scan_path}")

    if progress_callback:
        progress_callback("Detecting cards...")

    # Detect cards
    detected = detect_cards_in_image(
        image,
        min_area_frac=min_area_frac,
        max_area_frac=max_area_frac,
        epsilon_frac=epsilon_frac,
    )

    if progress_callback:
        progress_callback(f"Found {len(detected)} cards")

    # Create output directories
    extracted_dir = deck_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = deck_dir / "manifest.jsonl"

    # Save debug image if requested
    if debug:
        debug_dir = deck_dir / "debug"
        debug_path = debug_dir / f"{scan_id}_annotated.png"
        draw_debug_image(image, detected, debug_path)
        if progress_callback:
            progress_callback(f"Debug image saved: {debug_path.name}")

    # Extract and save each card
    crops = []
    for i, card in enumerate(detected):
        if progress_callback:
            progress_callback(f"Extracting card {i + 1}/{len(detected)}")

        # Get next crop ID
        crop_id = get_next_crop_id(manifest_path)

        # Extract with perspective transform
        warped = perspective_transform(image, card.corners, target_height)

        # Save crop
        crop_filename = f"{crop_id}.png"
        crop_path = extracted_dir / crop_filename
        cv2.imwrite(str(crop_path), warped)

        # Create metadata
        meta = CardCropMeta(
            crop_id=crop_id,
            file=f"extracted/{crop_filename}",
            source_scan_id=scan_id,
            bbox=card.bbox,
            corners=card.corners.astype(int).tolist(),
        )

        # Append to manifest
        append_record(manifest_path, meta)
        crops.append(meta)

    if progress_callback:
        progress_callback(f"Extracted {len(crops)} cards")

    return crops


def detect_single_image(
    image_path: Path,
    output_dir: Path,
    target_height: int = DEFAULT_TARGET_HEIGHT,
    min_area_frac: float = 0.3,  # Higher threshold for single-card images
    max_area_frac: float = 0.99,
    debug: bool = False,
) -> Path | None:
    """Detect and extract a single card from an image (for testing).

    This is useful for processing individual card photos rather than scans.

    Args:
        image_path: Path to image
        output_dir: Directory for output
        target_height: Resize to this height
        min_area_frac: Minimum area fraction (higher for single cards)
        max_area_frac: Maximum area fraction
        debug: Save debug image

    Returns:
        Path to extracted card or None if not detected
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    detected = detect_cards_in_image(
        image,
        min_area_frac=min_area_frac,
        max_area_frac=max_area_frac,
    )

    if debug:
        debug_path = output_dir / f"{image_path.stem}_debug.png"
        draw_debug_image(image, detected, debug_path)

    if not detected:
        return None

    # Take the largest detected card
    card = max(detected, key=lambda c: c.area)

    # Extract
    warped = perspective_transform(image, card.corners, target_height)

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{image_path.stem}_crop.png"
    cv2.imwrite(str(output_path), warped)

    return output_path
