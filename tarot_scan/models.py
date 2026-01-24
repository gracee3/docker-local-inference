"""Pydantic data models for tarot scan records."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScanMeta(BaseModel):
    """Metadata for a full-bed scan."""

    type: Literal["scan"] = "scan"
    scan_id: str
    file: str
    timestamp: datetime
    dpi: int
    device: str


class CardCropMeta(BaseModel):
    """Metadata for an extracted card crop."""

    type: Literal["crop"] = "crop"
    crop_id: str
    file: str
    source_scan_id: str
    bbox: tuple[int, int, int, int]  # x, y, w, h
    corners: list[list[int]]  # 4 corner points [[x,y], ...]


class CardClassification(BaseModel):
    """VLM classification result for a tarot card."""

    deck_hint: str | None = Field(
        default=None, description="Deck name if recognizable from art style"
    )
    card_name: str = Field(description="Full card name, e.g. 'Three of Wands'")
    arcana: Literal["major", "minor"] = Field(description="Major or minor arcana")
    suit: Literal["wands", "cups", "swords", "pentacles"] | None = Field(
        default=None, description="Suit for minor arcana, null for major"
    )
    rank: str | None = Field(
        default=None,
        description="Rank: ace, 2-10, page, knight, queen, king; null for major arcana",
    )
    major_number: int | None = Field(
        default=None, description="0-21 for major arcana, null for minor"
    )
    orientation: Literal["upright", "reversed", "unknown"] = Field(
        default="unknown", description="Card orientation"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    notes: str = Field(default="", description="Additional observations")


class ClassRecord(BaseModel):
    """Classification record linking a crop to its VLM result."""

    type: Literal["class"] = "class"
    crop_id: str
    model: str
    timestamp: datetime = Field(default_factory=datetime.now)
    result: CardClassification


# Union type for manifest records
ManifestRecord = ScanMeta | CardCropMeta | ClassRecord
