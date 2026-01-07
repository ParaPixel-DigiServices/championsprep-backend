"""
Quiz System Pydantic Models
Session management, answers, results, and analysis
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# REQUEST MODELS
# ============================================================================

class QuizStartRequest(BaseModel):
    """Request to start a new quiz session."""
    
    quiz_type: str = Field(..., description="Type: mcq, adaptive, timed, mock_exam")
    topic: Optional[str] = Field(None, description="Specific topic to quiz on")
    chapter_id: Optional[str] = Field(None, description="Specific chapter")
    difficulty: Optional[str] = Field(None, description="easy, medium, hard (ignored for adaptive)")
    question_count: int = Field(10, ge=5, le=100, description="Number of questions")
    time_per_question: Optional[int] = Field(None, description="Seconds per question (for timed quizzes)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "quiz_type": "mcq",
                "topic": "Introduction to Economics",
                "difficulty": "medium",
                "question_count": 20
            }
        }


class QuizAnswerRequest(BaseModel):
    """Submit answer for a question."""
    
    question_id: str
    selected_answer: str = Field(..., description="Selected option key (A/B/C/D)")
    time_spent_seconds: int = Field(default=0, ge=0)
    show_explanation: bool = Field(default=False, description="Show explanation if wrong")


class QuizSubmitRequest(BaseModel):
    """Submit completed quiz."""
    
    session_id: str
    force_submit: bool = Field(default=False, description="Force submit even if questions remain")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class QuizSessionResponse(BaseModel):
    """Response when starting a quiz."""
    
    session_id: str
    quiz_type: str
    total_questions: int
    time_limit_minutes: Optional[int] = None
    current_question: Dict[str, Any]
    current_question_number: int
    can_skip: bool = True
    can_go_back: bool = True
    started_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "quiz_type": "mcq",
                "total_questions": 20,
                "time_limit_minutes": 40,
                "current_question": {
                    "id": "q1",
                    "question_text": "What is GDP?",
                    "options": [
                        {"key": "A", "text": "Gross Domestic Product"},
                        {"key": "B", "text": "General Domestic Product"},
                        {"key": "C", "text": "Gross Development Product"},
                        {"key": "D", "text": "None of the above"}
                    ],
                    "difficulty": "easy",
                    "marks": 1
                },
                "current_question_number": 1,
                "can_skip": True,
                "can_go_back": True,
                "started_at": "2024-01-06T10:00:00Z"
            }
        }


class QuizResultResponse(BaseModel):
    """Quiz completion results."""
    
    session_id: str
    quiz_type: Optional[str] = None
    total_questions: int
    attempted_questions: Optional[int] = None
    correct_answers: int
    accuracy: float
    time_spent_minutes: float
    coins_earned: int
    performance_level: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    questions_breakdown: Optional[List[Dict[str, Any]]] = None
    completed_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "quiz_type": "mcq",
                "total_questions": 20,
                "attempted_questions": 20,
                "correct_answers": 16,
                "accuracy": 80.0,
                "time_spent_minutes": 35.5,
                "coins_earned": 15,
                "performance_level": "Good",
                "analysis": {
                    "difficulty_breakdown": {
                        "easy": {"correct": 8, "total": 10},
                        "medium": {"correct": 6, "total": 8},
                        "hard": {"correct": 2, "total": 2}
                    },
                    "average_time_per_question": 106.5,
                    "strengths": ["Quick problem solving", "Good accuracy"],
                    "areas_to_improve": []
                },
                "completed_at": "2024-01-06T10:35:30Z"
            }
        }


class QuizAnalysisResponse(BaseModel):
    """Detailed quiz performance analysis."""
    
    session_id: str
    overall_accuracy: float
    difficulty_breakdown: Dict[str, Dict[str, int]]
    topic_breakdown: Dict[str, Dict[str, int]]
    time_analysis: Dict[str, float]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "overall_accuracy": 80.0,
                "difficulty_breakdown": {
                    "easy": {"correct": 8, "total": 10, "accuracy": 80},
                    "medium": {"correct": 6, "total": 8, "accuracy": 75},
                    "hard": {"correct": 2, "total": 2, "accuracy": 100}
                },
                "topic_breakdown": {
                    "Microeconomics": {"correct": 8, "total": 10},
                    "Macroeconomics": {"correct": 8, "total": 10}
                },
                "time_analysis": {
                    "average_per_question": 106.5,
                    "fastest_question": 45,
                    "slowest_question": 180,
                    "total_time_minutes": 35.5
                },
                "strengths": [
                    "Excellent performance on hard questions (100%)",
                    "Quick problem solving (avg 1:46/question)"
                ],
                "weaknesses": [
                    "Medium difficulty questions need improvement (75%)"
                ],
                "recommendations": [
                    "Practice more medium difficulty questions",
                    "Focus on Macroeconomics concepts"
                ]
            }
        }


class QuizHistoryResponse(BaseModel):
    """User's quiz history."""
    
    session_id: str
    quiz_type: str
    topic: Optional[str]
    total_questions: int
    correct_answers: int
    accuracy: float
    time_spent_minutes: float
    coins_earned: int
    started_at: str
    completed_at: str
    
    class Config:
        from_attributes = True


class QuizStatsResponse(BaseModel):
    """Overall quiz statistics for user."""
    
    total_quizzes: int
    total_questions_attempted: int
    overall_accuracy: float
    total_time_spent_minutes: float
    total_coins_earned: int
    average_quiz_score: float
    best_quiz_accuracy: float
    recent_quizzes: List[QuizHistoryResponse]
    accuracy_trend: List[Dict[str, Any]]  # Last 10 quizzes
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_quizzes": 45,
                "total_questions_attempted": 900,
                "overall_accuracy": 78.5,
                "total_time_spent_minutes": 1350.5,
                "total_coins_earned": 675,
                "average_quiz_score": 78.5,
                "best_quiz_accuracy": 95.0,
                "recent_quizzes": [],
                "accuracy_trend": [
                    {"quiz_number": 1, "accuracy": 75},
                    {"quiz_number": 2, "accuracy": 78},
                    {"quiz_number": 3, "accuracy": 82}
                ]
            }
        }