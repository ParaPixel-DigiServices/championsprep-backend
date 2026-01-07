"""
Flashcard System Models
Decks, cards, reviews, and SRS tracking
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# FLASHCARD MODELS
# ============================================================================

class FlashCard(BaseModel):
    """Single flashcard."""
    front: str = Field(..., description="Question or term")
    back: str = Field(..., description="Answer or definition")
    hint: Optional[str] = Field(None, description="Optional hint")
    explanation: Optional[str] = Field(None, description="Additional context")


# ============================================================================
# DECK REQUEST MODELS
# ============================================================================

class DeckCreateRequest(BaseModel):
    """Create new flashcard deck."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    chapter_id: Optional[str] = None
    topic_id: Optional[str] = None
    cards: Optional[List[FlashCard]] = Field(default=[], description="Initial cards")
    enable_srs: bool = Field(default=True, description="Enable Spaced Repetition")
    is_public: bool = Field(default=False, description="Share with others")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Economics Chapter 1 - Key Terms",
                "description": "Important terms and definitions",
                "cards": [
                    {
                        "front": "What is GDP?",
                        "back": "Gross Domestic Product - total value of goods and services",
                        "hint": "Three words starting with G, D, P"
                    }
                ],
                "enable_srs": True,
                "is_public": False
            }
        }


class DeckUpdateRequest(BaseModel):
    """Update deck details."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    cards: Optional[List[FlashCard]] = None
    is_public: Optional[bool] = None


class CardPracticeRequest(BaseModel):
    """Practice a card (non-SRS mode)."""
    card_index: int = Field(..., ge=0, description="Index of card in deck")
    marked_as_known: bool = Field(..., description="Did user know the answer?")
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class SRSReviewRequest(BaseModel):
    """Review a card with SRS quality rating."""
    card_id: str = Field(..., description="Card identifier")
    quality: int = Field(..., ge=0, le=5, description="Quality rating 0-5")
    time_spent_seconds: Optional[int] = Field(None, ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "card_id": "0",
                "quality": 4,
                "time_spent_seconds": 15
            }
        }


# ============================================================================
# DECK RESPONSE MODELS
# ============================================================================

class DeckResponse(BaseModel):
    """Flashcard deck response."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    chapter_id: Optional[str] = None
    topic_id: Optional[str] = None
    cards: List[Dict[str, Any]]
    total_cards: int
    mastered_cards: int
    learning_cards: int
    enable_srs: bool
    is_public: bool
    total_reviews: int
    last_reviewed_at: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class CardReviewResponse(BaseModel):
    """Response after reviewing a card."""
    message: str
    next_review_date: str
    interval_days: int
    easiness_factor: float
    mastery_level: str  # learning, young, mature, mastered


class DeckStatsResponse(BaseModel):
    """Deck statistics."""
    deck_id: str
    deck_name: str
    total_cards: int
    new_cards: int
    learning_cards: int
    young_cards: int
    mature_cards: int
    mastered_cards: int
    due_today: int
    total_reviews: int
    last_reviewed_at: Optional[str] = None
    average_ease_factor: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "deck_id": "123e4567-e89b-12d3-a456-426614174000",
                "deck_name": "Economics Terms",
                "total_cards": 50,
                "new_cards": 10,
                "learning_cards": 15,
                "young_cards": 12,
                "mature_cards": 8,
                "mastered_cards": 5,
                "due_today": 8,
                "total_reviews": 245,
                "last_reviewed_at": "2024-01-06T10:00:00Z",
                "average_ease_factor": 2.5
            }
        }


class DueCardsResponse(BaseModel):
    """Cards due for review."""
    deck_id: str
    new_cards: List[Dict[str, Any]]
    due_cards: List[Dict[str, Any]]
    total_due: int