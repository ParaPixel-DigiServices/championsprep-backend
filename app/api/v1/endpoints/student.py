"""
Student Content Retrieval APIs
Browse chapters, get questions, track attempts, adaptive learning
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.api.v1.dependencies import get_current_user
from app.db.supabase import supabase
from app.models.auth import UserResponse as User
from app.models.content import (
    ChapterResponse,
    TopicResponse,
    ContentRequest,
    QuestionResponse,
    AttemptTrackingRequest
)

router = APIRouter(prefix="/student", tags=["Student Content"])
logger = logging.getLogger(__name__)


# ============================================================================
# BROWSE CONTENT
# ============================================================================

@router.get("/chapters", response_model=List[ChapterResponse])
async def get_my_chapters(
    current_user: User = Depends(get_current_user)
):
    """
    Get all chapters for student's grade level and board.
    """
    # FIXED: Use correct table name and add fallback
    try:
        profile = supabase.table("student_profiles").select("*").eq(
            "user_id", current_user.id
        ).execute()
        
        if profile.data:
            user_profile = profile.data[0]
            grade = user_profile.get("class")  # Note: "class" field in student_profiles
            board = user_profile.get("board", "CBSE")
            subjects = user_profile.get("subjects", [])
        else:
            # Fallback: Get from users table directly
            user = supabase.table("users").select("*").eq("id", current_user.id).execute()
            if not user.data:
                raise HTTPException(status_code=404, detail="User not found")
            
            user_data = user.data[0]
            grade = user_data.get("grade_level")
            board = "CBSE"  # Default
            subjects = []
    
    except Exception as e:
        # Last fallback: Just get all chapters
        grade = None
        board = "CBSE"
        subjects = []
    
    # Get chapters
    chapters_query = supabase.table("chapters").select(
        "*, topics(id, topic_name, difficulty_level)"
    )
    
    # Filter by board if we have it
    if board:
        chapters_query = chapters_query.eq("board", board)
    
    chapters_result = chapters_query.execute()
    
    if not chapters_result.data:
        return []
    
    # Filter by subjects if specified
    if subjects:
        chapters = [
            ch for ch in chapters_result.data 
            if any(subj.lower() in ch.get("chapter_name", "").lower() for subj in subjects)
        ]
    else:
        chapters = chapters_result.data
    
    return chapters


@router.get("/materials")
async def get_materials(
    current_user: User = Depends(get_current_user)
):
    """
    Get all available study materials.
    Simple endpoint without complex profile checks.
    """
    try:
        materials = supabase.table("uploaded_materials").select(
            "*"
        ).eq("processing_status", "completed").execute()
        
        return {
            "success": True,
            "materials": materials.data if materials.data else [],
            "count": len(materials.data) if materials.data else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chapters/{chapter_id}/topics", response_model=List[TopicResponse])
async def get_chapter_topics(
    chapter_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all topics for a specific chapter."""
    topics = supabase.table("topics").select("*").eq(
        "chapter_id", chapter_id
    ).order("topic_name").execute()  # Changed from display_order to topic_name
    
    return topics.data if topics.data else []


# ============================================================================
# GET QUESTIONS (WITH UNIQUENESS)
# ============================================================================

@router.post("/questions", response_model=List[QuestionResponse])
async def get_questions(
    request: ContentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Get questions with uniqueness tracking.
    Never shows the same question twice to a user.
    """
    # Get user's attempted questions
    attempted = supabase.table("user_question_attempts").select(
        "content_id"
    ).eq("user_id", current_user.id).execute()
    
    attempted_ids = [a["content_id"] for a in attempted.data] if attempted.data else []
    
    # Build query
    query = supabase.table("ai_generated_content").select("*")
    
    # Filter by content type
    if request.content_type:
        query = query.eq("content_type", request.content_type)
    
    # Filter by chapter
    if request.chapter_id:
        query = query.eq("chapter_id", request.chapter_id)
    
    # Filter by topic
    if request.topic:
        query = query.eq("topic", request.topic)
    
    # Filter by difficulty
    if request.difficulty:
        query = query.eq("difficulty_level", request.difficulty)
    
    # Exclude attempted questions
    if request.exclude_attempted and attempted_ids:
        query = query.not_.in_("id", attempted_ids)
    
    # Limit results
    query = query.limit(request.limit)
    
    result = query.execute()
    
    if not result.data:
        # If no new questions, optionally return attempted ones
        if not request.exclude_attempted:
            return []
        
        # Reset exclusion and try again
        result = supabase.table("ai_generated_content").select("*").eq(
            "content_type", request.content_type
        ).limit(request.limit).execute()
    
    return result.data if result.data else []


@router.get("/questions/random", response_model=List[QuestionResponse])
async def get_random_questions(
    content_type: str = Query(..., description="Type: mcq_easy, mcq_medium, mcq_hard, flashcard"),
    count: int = Query(10, ge=1, le=50),
    difficulty: Optional[str] = Query(None, description="easy, medium, hard"),
    exclude_attempted: bool = Query(True, description="Exclude previously attempted"),
    current_user: User = Depends(get_current_user)
):
    """
    Get random questions for practice.
    Perfect for daily practice sessions.
    """
    # Get attempted questions
    attempted = supabase.table("user_question_attempts").select(
        "content_id"
    ).eq("user_id", current_user.id).execute()
    
    attempted_ids = [a["content_id"] for a in attempted.data] if attempted.data else []
    
    # Build query
    query = supabase.table("ai_generated_content").select("*").eq(
        "content_type", content_type
    )
    
    if difficulty:
        query = query.eq("difficulty_level", difficulty)
    
    if exclude_attempted and attempted_ids:
        query = query.not_.in_("id", attempted_ids)
    
    # Get random sample
    query = query.limit(count)
    
    result = query.execute()
    
    return result.data if result.data else []


# ============================================================================
# STUDY SESSIONS
# ============================================================================

@router.post("/sessions/start")
async def start_study_session(
    session_type: str = Query("study_mode", description="Type: study_mode, mcq_quiz, flashcards, case_study, ai_tutor, mock_exam, adaptive_quiz"),
    current_user: User = Depends(get_current_user)
):
    """
    Start a new study session.
    Call this before attempting questions to get a session_id.
    
    Session types (as per database constraint):
    - study_mode: Regular study/practice mode (default)
    - mcq_quiz: MCQ quiz mode
    - flashcards: Flashcard practice
    - case_study: Case study mode
    - ai_tutor: AI tutor interaction
    - mock_exam: Mock examination
    - adaptive_quiz: Adaptive difficulty quiz
    """
    try:
        # Validate session_type against database constraint
        valid_types = [
            "mcq_quiz",
            "flashcards", 
            "case_study",
            "study_mode",
            "ai_tutor",
            "mock_exam",
            "adaptive_quiz"
        ]
        
        if session_type not in valid_types:
            session_type = "study_mode"  # Default fallback
        
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "session_type": session_type,
            "started_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("study_sessions").insert(session_data).execute()
        
        return {
            "session_id": session_data["id"],
            "started_at": session_data["started_at"],
            "session_type": session_data["session_type"],
            "message": "Study session started successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.post("/sessions/{session_id}/end")
async def end_study_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    End a study session.
    Records end time for the session.
    """
    try:
        # Verify session belongs to user
        session = supabase.table("study_sessions").select("*").eq(
            "id", session_id
        ).eq("user_id", current_user.id).execute()
        
        if not session.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session
        update_data = {
            "ended_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("study_sessions").update(update_data).eq("id", session_id).execute()
        
        return {
            "message": "Study session ended successfully",
            "session_id": session_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to end session: {str(e)}")


@router.get("/sessions/active")
async def get_active_session(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's active study session if one exists.
    Active = started but not ended (ended_at is null).
    Returns null if no active session.
    """
    try:
        # Get most recent session without ended_at
        session = supabase.table("study_sessions").select("*").eq(
            "user_id", current_user.id
        ).is_("ended_at", "null").order("started_at", desc=True).limit(1).execute()
        
        if session.data:
            return {
                "session": session.data[0],
                "has_active_session": True
            }
        else:
            return {
                "session": None,
                "has_active_session": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active session: {str(e)}")


# ============================================================================
# TRACK ATTEMPTS (UNIQUENESS SYSTEM)
# ============================================================================

@router.post("/attempts/track")
async def track_question_attempt(
    request: AttemptTrackingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Track that user has seen/attempted this question.
    Ensures uniqueness - won't show this question again.
    
    Requires a valid session_id from /sessions/start endpoint.
    """
    try:
        # Validate session_id is provided
        if not request.session_id:
            raise HTTPException(
                status_code=400, 
                detail="session_id is required. Call /student/sessions/start first."
            )
        
        # Verify session exists and belongs to user
        session = supabase.table("study_sessions").select("*").eq(
            "id", request.session_id
        ).eq("user_id", current_user.id).execute()
        
        if not session.data:
            raise HTTPException(
                status_code=404, 
                detail="Invalid session_id. Please start a new session."
            )
        
        # Check if already tracked
        existing = supabase.table("user_question_attempts").select("*").eq(
            "user_id", current_user.id
        ).eq("content_id", request.content_id).execute()
        
        if existing.data:
            return {"message": "Already tracked", "tracked": True}
        
        # Track new attempt
        attempt_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "content_id": request.content_id,
            "session_id": request.session_id,
            "is_correct": request.is_correct,
            "time_taken_seconds": request.time_spent_seconds,
            "attempted_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("user_question_attempts").insert(attempt_data).execute()
        
        return {
            "message": "Attempt tracked successfully", 
            "tracked": True,
            "session_id": request.session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track attempt: {str(e)}")


# ============================================================================
# ADAPTIVE CONTENT
# ============================================================================

@router.get("/adaptive/next")
async def get_adaptive_questions(
    topic: Optional[str] = None,
    count: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user)
):
    """
    Get adaptive questions based on user's performance.
    
    Logic:
    - If accuracy < 60%: Give easy questions
    - If accuracy 60-80%: Give medium questions
    - If accuracy > 80%: Give hard questions
    """
    # Get user's recent performance
    recent_attempts = supabase.table("user_question_attempts").select(
        "*"
    ).eq("user_id", current_user.id).order(
        "attempted_at", desc=True
    ).limit(20).execute()
    
    # Calculate accuracy
    if recent_attempts.data:
        correct = sum(1 for a in recent_attempts.data if a.get("is_correct"))
        accuracy = (correct / len(recent_attempts.data)) * 100
    else:
        accuracy = 0  # New user, start with easy
    
    # Determine difficulty
    if accuracy < 60:
        difficulty = "easy"
    elif accuracy < 80:
        difficulty = "medium"
    else:
        difficulty = "hard"
    
    # Get questions
    query = supabase.table("ai_generated_content").select("*").eq(
        "content_type", f"mcq_{difficulty}"
    )
    
    if topic:
        query = query.eq("topic", topic)
    
    # Exclude attempted
    attempted_ids = [a["content_id"] for a in recent_attempts.data]
    if attempted_ids:
        query = query.not_.in_("id", attempted_ids)
    
    query = query.limit(count)
    result = query.execute()
    
    return {
        "questions": result.data if result.data else [],
        "suggested_difficulty": difficulty,
        "current_accuracy": accuracy,
        "message": f"Based on {accuracy:.0f}% accuracy, showing {difficulty} questions"
    }


# ============================================================================
# STUDY STATS
# ============================================================================

@router.get("/stats")
async def get_study_stats(
    current_user: User = Depends(get_current_user)
):
    """Get user's study statistics."""
    
    # Get all attempts
    attempts = supabase.table("user_question_attempts").select("*").eq(
        "user_id", current_user.id
    ).execute()
    
    if not attempts.data:
        return {
            "total_questions_attempted": 0,
            "correct_answers": 0,
            "accuracy": 0,
            "total_time_spent_minutes": 0,
            "average_time_per_question": 0,
            "topics_covered": []
        }
    
    total = len(attempts.data)
    correct = sum(1 for a in attempts.data if a.get("is_correct"))
    total_time = sum(a.get("time_spent_seconds", 0) for a in attempts.data)
    
    # Get topics covered
    topics_result = supabase.table("ai_generated_content").select(
        "topic"
    ).in_("id", [a["content_id"] for a in attempts.data]).execute()
    
    topics = list(set([t["topic"] for t in topics_result.data if t.get("topic")])) if topics_result.data else []
    
    return {
        "total_questions_attempted": total,
        "correct_answers": correct,
        "accuracy": round((correct / total) * 100, 2) if total > 0 else 0,
        "total_time_spent_minutes": round(total_time / 60, 2),
        "average_time_per_question": round(total_time / total, 2) if total > 0 else 0,
        "topics_covered": topics,
        "topics_count": len(topics)
    }


# ============================================================================
# QUIZ ENDPOINTS
# ============================================================================

@router.post("/quiz/start")
async def start_quiz(
    quiz_request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Start a new quiz.
    
    Request body:
    {
        "quiz_type": "mcq",
        "chapter_id": "uuid",
        "difficulty": "easy|medium|hard",
        "question_count": 10
    }
    """
    try:
        quiz_type = quiz_request.get("quiz_type", "mcq")
        chapter_id = quiz_request.get("chapter_id")
        difficulty = quiz_request.get("difficulty", "medium")
        question_count = quiz_request.get("question_count", 10)
        
        if not chapter_id:
            raise HTTPException(status_code=400, detail="chapter_id is required")
        
        # Map content type based on quiz type and difficulty
        if quiz_type == "mcq":
            content_type = f"mcq_{difficulty}"
        else:
            content_type = quiz_type
        
        logger.info(f"Searching for content_type: {content_type}, chapter: {chapter_id}")
        
        # First, check what content exists for this chapter
        all_content = supabase.table("ai_generated_content").select("content_type").eq(
            "chapter_id", chapter_id
        ).execute()
        
        available_types = [item["content_type"] for item in all_content.data] if all_content.data else []
        logger.info(f"Available content types for chapter: {available_types}")
        
        # Get questions for this chapter
        query = supabase.table("ai_generated_content").select("*").eq(
            "chapter_id", chapter_id
        ).eq("content_type", content_type)
        
        # Get user's attempted questions to exclude them
        attempted = supabase.table("user_question_attempts").select(
            "content_id"
        ).eq("user_id", current_user.id).execute()
        
        attempted_ids = [a["content_id"] for a in attempted.data] if attempted.data else []
        logger.info(f"User has attempted {len(attempted_ids)} questions")
        
        if attempted_ids:
            query = query.not_.in_("id", attempted_ids)
        
        result = query.execute()
        
        logger.info(f"Found {len(result.data) if result.data else 0} content items")
        
        if not result.data:
            # Provide helpful error message
            if not available_types:
                raise HTTPException(
                    status_code=404,
                    detail=f"No content found for this chapter. Please process the material first."
                )
            elif content_type not in available_types:
                raise HTTPException(
                    status_code=404,
                    detail=f"No '{difficulty}' difficulty questions found. Available: {', '.join(available_types)}"
                )
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"All '{difficulty}' questions have been attempted. Try a different difficulty."
                )
        
        # Start a quiz session
        session_data = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "session_type": "mcq_quiz",
            "started_at": datetime.utcnow().isoformat()
        }
        
        session = supabase.table("study_sessions").insert(session_data).execute()
        
        # Extract questions from content
        questions = []
        for item in result.data:
            content = item.get("content", [])
            if isinstance(content, list):
                # Content is array of questions
                questions.extend(content)
            elif isinstance(content, dict):
                # Content is single question
                questions.append(content)
        
        logger.info(f"Extracted {len(questions)} total questions")
        
        # Limit to requested count
        questions = questions[:question_count]
        
        if not questions:
            raise HTTPException(
                status_code=404,
                detail="Questions found but content format is invalid"
            )
        
        return {
            "session_id": session_data["id"],
            "quiz_type": quiz_type,
            "difficulty": difficulty,
            "total_questions": len(questions),
            "questions": questions,
            "time_limit_seconds": len(questions) * 60,
            "message": "Quiz started successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quiz start error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start quiz: {str(e)}")


@router.post("/quiz/{session_id}/submit")
async def submit_quiz(
    session_id: str,
    answers: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit quiz answers and get results."""
    try:
        # Verify session
        session = supabase.table("study_sessions").select("*").eq(
            "id", session_id
        ).eq("user_id", current_user.id).execute()
        
        if not session.data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Process answers
        answer_list = answers.get("answers", [])
        correct_count = 0
        total_time = 0
        
        for answer in answer_list:
            content_id = answer.get("content_id")
            selected = answer.get("selected_answer")
            time_spent = answer.get("time_spent", 0)
            
            # Get question
            question = supabase.table("ai_generated_content").select("*").eq(
                "id", content_id
            ).execute()
            
            is_correct = False
            if question.data:
                content = question.data[0].get("content", [])
                if isinstance(content, list):
                    for q in content:
                        if isinstance(q, dict) and q.get("correct_answer") == selected:
                            is_correct = True
                            break
            
            if is_correct:
                correct_count += 1
            
            total_time += time_spent
            
            # Track attempt
            attempt_data = {
                "id": str(uuid.uuid4()),
                "user_id": current_user.id,
                "content_id": content_id,
                "session_id": session_id,
                "is_correct": is_correct,
                "time_taken_seconds": time_spent,
                "attempted_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("user_question_attempts").insert(attempt_data).execute()
        
        # End session
        supabase.table("study_sessions").update({
            "ended_at": datetime.utcnow().isoformat()
        }).eq("id", session_id).execute()
        
        # Calculate results
        total_questions = len(answer_list)
        score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "session_id": session_id,
            "total_questions": total_questions,
            "correct_answers": correct_count,
            "wrong_answers": total_questions - correct_count,
            "score_percentage": round(score_percentage, 2),
            "total_time_seconds": total_time,
            "average_time_per_question": round(total_time / total_questions, 2) if total_questions > 0 else 0,
            "passed": score_percentage >= 60,
            "message": "Quiz submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit quiz: {str(e)}")