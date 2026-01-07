"""
Pydantic models for content management and AI generation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class ProcessingStatus(str, Enum):
    """Material processing status."""
    PENDING = "pending"
    EXTRACTING = "extracting"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


class DifficultyLevel(str, Enum):
    """Question difficulty level."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ContentType(str, Enum):
    """AI-generated content type."""
    MCQ = "mcq"
    FLASHCARD = "flashcard"
    CASE_STUDY = "case_study"
    SUMMARY = "summary"
    MIND_MAP = "mind_map"
    EXAM_QUESTION = "exam_question"


# ============================================================================
# UPLOAD MODELS
# ============================================================================

class MaterialUploadResponse(BaseModel):
    """Response after uploading study material."""
    
    id: str
    filename: str
    file_url: str
    file_size_bytes: int
    processing_status: ProcessingStatus
    uploaded_by: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# CHAPTER MODELS
# ============================================================================

class ChapterResponse(BaseModel):
    """AI-extracted chapter."""
    
    id: str
    chapter_number: int
    chapter_name: str
    chapter_description: Optional[str] = None
    board: Optional[str] = None
    extraction_confidence: Optional[float] = None
    is_validated: bool
    display_order: Optional[int] = None
    
    model_config = {"from_attributes": True}


class ChapterListResponse(BaseModel):
    """List of chapters."""
    
    chapters: List[ChapterResponse]
    total: int


# ============================================================================
# TOPIC MODELS
# ============================================================================

class TopicResponse(BaseModel):
    """AI-extracted topic/subtopic."""
    
    id: str
    topic_name: str
    topic_description: Optional[str] = None
    topic_level: int
    difficulty_level: Optional[DifficultyLevel] = None
    is_validated: bool
    display_order: Optional[int] = None
    
    model_config = {"from_attributes": True}


class TopicListResponse(BaseModel):
    """List of topics for a chapter."""
    
    topics: List[TopicResponse]
    total: int


# ============================================================================
# AI GENERATION MODELS
# ============================================================================

class MCQOption(BaseModel):
    """MCQ option."""
    
    option_key: str  # A, B, C, D
    option_text: str


class MCQQuestion(BaseModel):
    """Multiple choice question."""
    
    question_text: str
    options: List[MCQOption]
    correct_answer: str  # A, B, C, or D
    explanation: str
    difficulty: DifficultyLevel
    marks: int = 1


class FlashcardContent(BaseModel):
    """Flashcard content."""
    
    front: str  # Question/Term
    back: str  # Answer/Definition
    hint: Optional[str] = None
    explanation: Optional[str] = None


class ExamSection(BaseModel):
    """Section in exam paper."""
    
    section: str  # "A", "B", "C"
    title: str
    marks: int
    questions: List[str]  # Question IDs


class ExamPaperStructure(BaseModel):
    """Complete exam paper structure."""
    
    title: str
    total_marks: int
    duration_minutes: int
    sections: List[ExamSection]


# ============================================================================
# AI EXTRACTION RESPONSE
# ============================================================================

class AIExtractionResult(BaseModel):
    """Result of AI extraction from PDF."""
    
    detected_class: str
    detected_board: str
    detected_subject: str
    chapters_extracted: int
    topics_extracted: int
    extraction_confidence: float
    processing_time_seconds: int


class AIGenerationResult(BaseModel):
    """Result of AI content generation."""
    
    mcqs_generated: int
    flashcards_generated: int
    exam_papers_generated: int
    total_tokens_used: int
    generation_time_seconds: int


# ============================================================================
# QUESTION ATTEMPT MODELS
# ============================================================================

class QuestionAttemptRequest(BaseModel):
    """Submit answer to a question."""
    
    content_id: str
    user_answer: str
    time_taken_seconds: int
    session_id: Optional[str] = None


class QuestionAttemptResponse(BaseModel):
    """Response after submitting answer."""
    
    is_correct: bool
    correct_answer: str
    explanation: str
    time_taken_seconds: int
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "is_correct": True,
                "correct_answer": "B",
                "explanation": "Option B is correct because...",
                "time_taken_seconds": 45
            }
        }
    }


# ============================================================================
# CONTENT RETRIEVAL MODELS
# ============================================================================

class ContentFilterRequest(BaseModel):
    """Filter for retrieving questions."""
    
    class_id: Optional[str] = None
    subject_id: Optional[str] = None
    chapter_id: Optional[str] = None
    topic_id: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    content_type: Optional[ContentType] = None
    exclude_attempted: bool = True  # Don't show questions user has already attempted
    limit: int = Field(default=10, ge=1, le=100)


class GeneratedContentResponse(BaseModel):
    """AI-generated content item."""
    
    id: str
    content_type: ContentType
    content: Dict[str, Any]  # Actual question/flashcard data
    difficulty_level: Optional[DifficultyLevel] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    is_validated: bool
    
    model_config = {"from_attributes": True}


# ============================================================================
# EXAM PAPER MODELS
# ============================================================================

class ExamPaperResponse(BaseModel):
    """Exam paper details."""
    
    id: str
    title: str
    description: Optional[str] = None
    board: Optional[str] = None
    total_marks: int
    duration_minutes: int
    sections: List[Dict[str, Any]]
    is_validated: bool
    times_attempted: int
    average_score: Optional[float] = None
    
    model_config = {"from_attributes": True}


class StartExamResponse(BaseModel):
    """Response when starting an exam."""
    
    attempt_id: str
    exam_paper: ExamPaperResponse
    started_at: datetime
    time_limit_minutes: int


class ExamAnswerSubmission(BaseModel):
    """Submit answers for exam."""
    
    attempt_id: str
    answers: Dict[str, str]  # question_id -> answer


class ExamResultResponse(BaseModel):
    """Exam result after submission."""
    
    attempt_id: str
    total_marks: int
    marks_obtained: float
    percentage: float
    time_taken_minutes: int
    section_wise_scores: List[Dict[str, Any]]
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "attempt_id": "123e4567-e89b-12d3-a456-426614174000",
                "total_marks": 80,
                "marks_obtained": 68.5,
                "percentage": 85.63,
                "time_taken_minutes": 165,
                "section_wise_scores": [
                    {"section": "A", "marks": 18, "total": 20},
                    {"section": "B", "marks": 25, "total": 30},
                    {"section": "C", "marks": 25.5, "total": 30}
                ]
            }
        }
    }


# ============================================================================
# PROCESSING STATUS MODELS
# ============================================================================

class ProcessingStatusResponse(BaseModel):
    """Current processing status of uploaded material."""
    
    material_id: str
    filename: str
    processing_status: ProcessingStatus
    progress_percentage: int
    current_step: Optional[str] = None
    chapters_extracted: int
    topics_extracted: int
    mcqs_generated: int
    flashcards_generated: int
    error_message: Optional[str] = None
    
    model_config = {"from_attributes": True}


# ============================================================================
# STUDENT CONTENT RETRIEVAL MODELS
# ============================================================================

class ContentRequest(BaseModel):
    """Student content request with filters."""
    content_type: Optional[str] = Field(None, description="Type: mcq_easy, mcq_medium, mcq_hard, flashcard, concept, etc.")
    chapter_id: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[str] = Field(None, description="easy, medium, hard")
    exclude_attempted: bool = Field(True, description="Exclude previously attempted questions")
    limit: int = Field(10, ge=1, le=50)


from typing import Union, List, Dict, Any

class QuestionResponse(BaseModel):
    """Question response model."""
    id: str
    content_type: str
    content: Union[Dict[str, Any], List[Dict[str, Any]]]  # ✅ Can be dict OR list
    difficulty_level: Optional[str] = None
    created_at: str
    
    model_config = {"from_attributes": True}


class AttemptTrackingRequest(BaseModel):
    """Track question attempt for uniqueness."""
    content_id: str
    session_id: Optional[str] = None
    is_correct: Optional[bool] = None
    time_spent_seconds: Optional[int] = None