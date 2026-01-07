"""
Quiz Session Management System
Complete quiz lifecycle: start → track → submit → analyze
Supports: MCQ, Adaptive, Timed, Mock Exams
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import random

from app.api.v1.dependencies import get_current_user
from app.db.supabase import supabase
from app.models.auth import UserResponse as User
from app.models.quiz import (
    QuizStartRequest,
    QuizSessionResponse,
    QuizAnswerRequest,
    QuizSubmitRequest,
    QuizResultResponse,
    QuizAnalysisResponse,
    QuizHistoryResponse
)

router = APIRouter(prefix="/quiz", tags=["Quiz System"])


# ============================================================================
# START QUIZ SESSION
# ============================================================================

@router.post("/start", response_model=QuizSessionResponse)
async def start_quiz(
    request: QuizStartRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Start a new quiz session.
    
    Quiz Types:
    - mcq: Standard MCQ quiz (fixed difficulty)
    - adaptive: Difficulty adjusts based on performance
    - timed: Time-bound quiz with countdown
    - mock_exam: Full board exam simulation
    """
    try:
        # Get questions based on request
        questions = await _get_quiz_questions(
            user_id=current_user.id,
            quiz_type=request.quiz_type,
            topic=request.topic,
            chapter_id=request.chapter_id,
            difficulty=request.difficulty,
            count=request.question_count
        )
        
        if not questions:
            raise HTTPException(status_code=404, detail="No questions found for selected criteria")
        
        # Calculate time limit
        time_limit = _calculate_time_limit(request.quiz_type, len(questions), request.time_per_question)
        
        # Create quiz session
        session_id = str(uuid.uuid4())
        session_data = {
            "id": session_id,
            "user_id": current_user.id,
            "quiz_type": request.quiz_type,
            "chapter_id": request.chapter_id,
            "topic_id": request.topic,  # Can be null
            "difficulty": request.difficulty,
            "total_questions": len(questions),
            "time_limit_minutes": time_limit,
            "started_at": datetime.utcnow().isoformat(),
            "status": "in_progress",
            "questions": [q["id"] for q in questions],
            "current_question_index": 0,
            "answers": {},
            "is_adaptive": request.quiz_type == "adaptive",
            "current_difficulty": request.difficulty or "medium"
        }
        
        # Store session in quiz_sessions table (not study_sessions)
        supabase.table("quiz_sessions").insert(session_data).execute()
        
        # Return first question (already formatted from _get_quiz_questions)
        return {
            "session_id": session_id,
            "quiz_type": request.quiz_type,
            "total_questions": len(questions),
            "time_limit_minutes": time_limit,
            "current_question": _format_question(questions[0]),
            "current_question_number": 1,
            "can_skip": request.quiz_type != "mock_exam",
            "can_go_back": request.quiz_type not in ["timed", "mock_exam"],
            "started_at": session_data["started_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start quiz: {str(e)}")


# ============================================================================
# GET NEXT QUESTION
# ============================================================================

@router.get("/{session_id}/next")
async def get_next_question(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get next question in quiz session."""
    
    # Get session from quiz_sessions table
    session = supabase.table("quiz_sessions").select("*").eq(
        "id", session_id
    ).eq("user_id", current_user.id).execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    
    session_data = session.data[0]
    
    # Check if quiz is finished
    if session_data["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Quiz already completed")
    
    # Check if quiz is finished
    current_index = session_data["current_question_index"]
    question_ids = session_data["questions"]
    
    if current_index >= len(question_ids):
        return {"message": "Quiz completed", "has_next": False}
    
    # Get next question
    question_id = question_ids[current_index]
    
    # Parse question ID to get content_id and index
    if "_q" in question_id:
        content_id = question_id.split("_q")[0]
        q_index = int(question_id.split("_q")[1])
    else:
        content_id = question_id
        q_index = 0
    
    question = supabase.table("ai_generated_content").select("*").eq(
        "id", content_id
    ).execute()
    
    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Extract the specific question from content array
    content = question.data[0].get("content", [])
    if isinstance(content, list) and q_index < len(content):
        question_obj = content[q_index]
        question_obj["id"] = question_id
    else:
        question_obj = content
    
    # For adaptive quiz, adjust difficulty if needed
    if session_data["is_adaptive"]:
        await _adjust_adaptive_difficulty(session_id, session_data)
    
    return {
        "session_id": session_id,
        "question": _format_question(question_obj),
        "question_number": current_index + 1,
        "total_questions": len(question_ids),
        "has_next": current_index + 1 < len(question_ids)
    }


# ============================================================================
# SUBMIT ANSWER
# ============================================================================

@router.post("/{session_id}/answer")
async def submit_answer(
    session_id: str,
    request: QuizAnswerRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit answer for current question."""
    
    # Get session from quiz_sessions
    session = supabase.table("quiz_sessions").select("*").eq(
        "id", session_id
    ).eq("user_id", current_user.id).execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    
    session_data = session.data[0]
    
    # Parse question_id to get content_id
    if "_q" in request.question_id:
        content_id = request.question_id.split("_q")[0]
        q_index = int(request.question_id.split("_q")[1])
    else:
        content_id = request.question_id
        q_index = 0
    
    # Get question
    question = supabase.table("ai_generated_content").select("*").eq(
        "id", content_id
    ).execute()
    
    if not question.data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    question_data = question.data[0]
    
    # Get correct answer from content
    content = question_data.get("content", [])
    correct_answer = None
    
    # Find the specific question in the content array
    if isinstance(content, list):
        # Content is array - find by question_id pattern
        q_index = int(request.question_id.split("_q")[-1]) if "_q" in request.question_id else 0
        if q_index < len(content):
            correct_answer = content[q_index].get("correct_answer")
    elif isinstance(content, dict):
        correct_answer = content.get("correct_answer")
    
    is_correct = request.selected_answer == correct_answer
    
    # Store answer
    answers = session_data.get("answers", {})
    answers[request.question_id] = {
        "selected_answer": request.selected_answer,
        "is_correct": is_correct,
        "time_spent": request.time_spent_seconds,
        "answered_at": datetime.utcnow().isoformat()
    }
    
    # Update session
    updates = {
        "answers": answers,
        "current_question_index": session_data["current_question_index"] + 1,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    supabase.table("quiz_sessions").update(updates).eq("id", session_id).execute()
    
    # Track attempt in uniqueness system
    # Use the full question_id (with _q index) as the unique identifier
    attempt_data = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "content_id": request.question_id,  # Use full question_id (e.g., "uuid_q3") for uniqueness
        "session_id": session_id,
        "is_correct": is_correct,
        "time_taken_seconds": request.time_spent_seconds,
        "attempted_at": datetime.utcnow().isoformat()
    }
    
    # Check if this specific question was already attempted in this session
    existing = supabase.table("user_question_attempts").select("id").eq(
        "user_id", current_user.id
    ).eq("content_id", request.question_id).eq("session_id", session_id).execute()
    
    if not existing.data:
        # Only insert if not already attempted
        supabase.table("user_question_attempts").insert(attempt_data).execute()
    else:
        # Update existing attempt
        supabase.table("user_question_attempts").update({
            "is_correct": is_correct,
            "time_taken_seconds": request.time_spent_seconds,
            "attempted_at": datetime.utcnow().isoformat()
        }).eq("id", existing.data[0]["id"]).execute()
    
    # Return immediate feedback if requested
    response = {
        "is_correct": is_correct,
        "has_next": updates["current_question_index"] < len(session_data["questions"])
    }
    
    if request.show_explanation and not is_correct:
        if isinstance(content, list) and q_index < len(content):
            response["explanation"] = content[q_index].get("explanation")
            response["correct_answer"] = correct_answer
        elif isinstance(content, dict):
            response["explanation"] = content.get("explanation")
            response["correct_answer"] = correct_answer
    
    return response


# ============================================================================
# SUBMIT QUIZ (COMPLETE)
# ============================================================================

@router.post("/{session_id}/submit", response_model=QuizResultResponse)
async def submit_quiz(
    session_id: str,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Complete quiz and get results.
    Calculates score, accuracy, time spent, and performance analysis.
    """
    
    # Get session
    session = supabase.table("quiz_sessions").select("*").eq(
        "id", session_id
    ).eq("user_id", current_user.id).execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    
    session_data = session.data[0]
    
    if session_data["status"] == "completed":
        raise HTTPException(status_code=400, detail="Quiz already submitted")
    
    # Calculate results
    answers = session_data.get("answers", {})
    total_questions = session_data["total_questions"]
    correct_answers = sum(1 for a in answers.values() if a.get("is_correct"))
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Calculate time spent
    started_at = datetime.fromisoformat(session_data["started_at"].replace('Z', '+00:00'))
    time_spent_minutes = (datetime.utcnow() - started_at.replace(tzinfo=None)).total_seconds() / 60
    
    # Award coins based on performance
    coins_earned = _calculate_coins(accuracy, session_data["quiz_type"])
    
    # Update session
    supabase.table("quiz_sessions").update({
        "status": "completed",
        "completed_at": datetime.utcnow().isoformat(),
        "correct_answers": correct_answers,
        "accuracy": accuracy,
        "time_spent_minutes": time_spent_minutes,
        "coins_earned": coins_earned
    }).eq("id", session_id).execute()
    
    # Update user coins
    background_tasks.add_task(_award_coins, current_user.id, coins_earned)
    
    # Generate performance analysis
    analysis = await _generate_analysis(session_id, session_data, answers)
    
    return {
        "session_id": session_id,
        "total_questions": total_questions,
        "attempted_questions": len(answers),
        "correct_answers": correct_answers,
        "accuracy": round(accuracy, 2),
        "time_spent_minutes": round(time_spent_minutes, 2),
        "coins_earned": coins_earned,
        "performance_level": _get_performance_level(accuracy),
        "analysis": analysis,
        "completed_at": datetime.utcnow().isoformat()
    }


# ============================================================================
# GET QUIZ RESULTS (REVIEW)
# ============================================================================

@router.get("/{session_id}/results", response_model=QuizResultResponse)
async def get_quiz_results(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed results of completed quiz for review."""
    
    session = supabase.table("quiz_sessions").select("*").eq(
        "id", session_id
    ).eq("user_id", current_user.id).execute()
    
    if not session.data:
        raise HTTPException(status_code=404, detail="Quiz session not found")
    
    session_data = session.data[0]
    
    if session_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Quiz not yet completed")
    
    # Get detailed question-by-question breakdown
    questions_with_answers = []
    for q_id in session_data["questions"]:
        # Extract content_id from question_id
        if "_q" in q_id:
            content_id = q_id.split("_q")[0]
            q_index = int(q_id.split("_q")[1])
        else:
            content_id = q_id
            q_index = 0
        
        question = supabase.table("ai_generated_content").select("*").eq("id", content_id).execute()
        if question.data:
            q_data = question.data[0]
            content = q_data.get("content", [])
            
            # Extract the specific question from array
            if isinstance(content, list) and q_index < len(content):
                question_content = content[q_index]
            elif isinstance(content, dict):
                question_content = content
            else:
                continue
            
            answer_data = session_data["answers"].get(q_id, {})
            
            questions_with_answers.append({
                "question": question_content,
                "your_answer": answer_data.get("selected_answer"),
                "correct_answer": question_content.get("correct_answer"),
                "is_correct": answer_data.get("is_correct"),
                "explanation": question_content.get("explanation"),
                "time_spent": answer_data.get("time_spent")
            })
    
    return {
        "session_id": session_id,
        "quiz_type": session_data["quiz_type"],
        "total_questions": session_data["total_questions"],
        "correct_answers": session_data["correct_answers"],
        "accuracy": session_data["accuracy"],
        "time_spent_minutes": session_data["time_spent_minutes"],
        "coins_earned": session_data["coins_earned"],
        "questions_breakdown": questions_with_answers,
        "completed_at": session_data["completed_at"]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _get_quiz_questions(
    user_id: str,
    quiz_type: str,
    topic: Optional[str],
    chapter_id: Optional[str],
    difficulty: Optional[str],
    count: int
) -> List[Dict]:
    """Get questions for quiz based on criteria."""
    
    # Get attempted questions for uniqueness
    attempted = supabase.table("user_question_attempts").select(
        "content_id"
    ).eq("user_id", user_id).execute()
    
    attempted_ids = [a["content_id"] for a in attempted.data] if attempted.data else []
    
    # Build query - map content type
    if difficulty:
        content_type = f"mcq_{difficulty}"
    else:
        content_type = "mcq_medium"
    
    query = supabase.table("ai_generated_content").select("*").eq(
        "content_type", content_type
    )
    
    if topic:
        query = query.eq("topic", topic)
    if chapter_id:
        query = query.eq("chapter_id", chapter_id)
    
    # Exclude attempted (but we need to check content IDs, not row IDs)
    # For now, don't filter by attempted since content is array
    
    result = query.execute()
    
    if not result.data:
        return []
    
    # Extract individual questions from content arrays
    all_questions = []
    for item in result.data:
        content = item.get("content", [])
        if isinstance(content, list):
            # Content is array of questions
            for idx, question in enumerate(content):
                if isinstance(question, dict):
                    # Add metadata
                    question["_content_id"] = item["id"]
                    question["_question_index"] = idx
                    question["id"] = f"{item['id']}_q{idx}"  # Unique ID per question
                    all_questions.append(question)
        elif isinstance(content, dict):
            # Content is single question
            content["_content_id"] = item["id"]
            content["id"] = item["id"]
            all_questions.append(content)
    
    # Now we have flat list of questions
    if not all_questions:
        return []
    
    # Shuffle and take requested count
    random.shuffle(all_questions)
    return all_questions[:count]


def _calculate_time_limit(quiz_type: str, question_count: int, time_per_question: Optional[int]) -> int:
    """Calculate quiz time limit in minutes."""
    if quiz_type == "mock_exam":
        return 180  # 3 hours for board exam
    elif time_per_question:
        return (time_per_question * question_count) // 60
    else:
        return question_count * 2  # Default: 2 minutes per question


def _format_question(question: Dict) -> Dict:
    """Format question for display (hide correct answer)."""
    # Question is already extracted from content array
    return {
        "id": question.get("id"),
        "question_text": question.get("question_text"),
        "options": question.get("options"),
        "difficulty": question.get("difficulty"),
        "marks": question.get("marks", 1)
    }


async def _adjust_adaptive_difficulty(session_id: str, session_data: Dict):
    """Adjust difficulty for adaptive quiz based on recent performance."""
    answers = session_data.get("answers", {})
    
    if len(answers) >= 3:  # Need at least 3 answers to adjust
        recent_answers = list(answers.values())[-3:]
        recent_correct = sum(1 for a in recent_answers if a.get("is_correct"))
        accuracy = (recent_correct / 3) * 100
        
        current_difficulty = session_data.get("current_difficulty", "medium")
        
        # Adjust difficulty
        if accuracy >= 80 and current_difficulty != "hard":
            new_difficulty = "hard"
        elif accuracy <= 40 and current_difficulty != "easy":
            new_difficulty = "easy"
        else:
            new_difficulty = current_difficulty
        
        if new_difficulty != current_difficulty:
            supabase.table("quiz_sessions").update({
                "current_difficulty": new_difficulty
            }).eq("id", session_id).execute()


def _calculate_coins(accuracy: float, quiz_type: str) -> int:
    """Calculate coins earned based on performance."""
    base_coins = {
        "mcq": 10,
        "adaptive": 15,
        "timed": 12,
        "mock_exam": 50
    }.get(quiz_type, 10)
    
    # Bonus for high accuracy
    if accuracy >= 90:
        return int(base_coins * 2)
    elif accuracy >= 75:
        return int(base_coins * 1.5)
    elif accuracy >= 60:
        return base_coins
    else:
        return int(base_coins * 0.5)


async def _award_coins(user_id: str, coins: int):
    """Award coins to user (background task)."""
    try:
        profile = supabase.table("user_profiles").select("coins").eq(
            "user_id", user_id
        ).execute()
        
        if profile.data:
            current_coins = profile.data[0].get("coins", 0)
            supabase.table("user_profiles").update({
                "coins": current_coins + coins
            }).eq("user_id", user_id).execute()
    except Exception as e:
        print(f"Failed to award coins: {str(e)}")


def _get_performance_level(accuracy: float) -> str:
    """Get performance level based on accuracy."""
    if accuracy >= 90:
        return "Excellent"
    elif accuracy >= 75:
        return "Good"
    elif accuracy >= 60:
        return "Average"
    else:
        return "Needs Improvement"


async def _generate_analysis(session_id: str, session_data: Dict, answers: Dict) -> Dict:
    """Generate detailed performance analysis."""
    
    # Analyze by difficulty
    difficulty_breakdown = {"easy": {"correct": 0, "total": 0}, "medium": {"correct": 0, "total": 0}, "hard": {"correct": 0, "total": 0}}
    
    for q_id, answer in answers.items():
        # Extract content_id from question_id (remove _qN suffix if present)
        if "_q" in q_id:
            content_id = q_id.split("_q")[0]
            q_index = int(q_id.split("_q")[1])
        else:
            content_id = q_id
            q_index = 0
        
        question = supabase.table("ai_generated_content").select("*").eq("id", content_id).execute()
        if question.data:
            content = question.data[0].get("content", [])
            
            # Get difficulty from the specific question in the array
            if isinstance(content, list) and q_index < len(content):
                diff = content[q_index].get("difficulty", "medium")
            elif isinstance(content, dict):
                diff = content.get("difficulty", "medium")
            else:
                diff = "medium"
            
            difficulty_breakdown[diff]["total"] += 1
            if answer.get("is_correct"):
                difficulty_breakdown[diff]["correct"] += 1
    
    return {
        "difficulty_breakdown": difficulty_breakdown,
        "average_time_per_question": sum(a.get("time_spent", 0) for a in answers.values()) / len(answers) if answers else 0,
        "strengths": ["Quick problem solving"] if session_data.get("time_spent_minutes", 0) < 30 else [],
        "areas_to_improve": ["Accuracy needs work"] if session_data.get("accuracy", 0) < 70 else []
    }


# ============================================================================
# QUIZ HISTORY & STATS
# ============================================================================

@router.get("/history", response_model=List[QuizHistoryResponse])
async def get_quiz_history(
    limit: int = Query(20, ge=1, le=100),
    quiz_type: Optional[str] = Query(None, description="Filter by quiz type"),
    current_user: User = Depends(get_current_user)
):
    """Get user's quiz history."""
    
    query = supabase.table("quiz_sessions").select("*").eq(
        "user_id", current_user.id
    ).eq("status", "completed").order("completed_at", desc=True).limit(limit)
    
    if quiz_type:
        query = query.eq("quiz_type", quiz_type)
    
    result = query.execute()
    
    return result.data if result.data else []


@router.get("/stats", response_model=Dict[str, Any])
async def get_quiz_stats(
    current_user: User = Depends(get_current_user)
):
    """Get overall quiz statistics."""
    
    # Get all completed quizzes
    quizzes = supabase.table("quiz_sessions").select("*").eq(
        "user_id", current_user.id
    ).eq("status", "completed").execute()
    
    if not quizzes.data:
        return {
            "total_quizzes": 0,
            "total_questions_attempted": 0,
            "overall_accuracy": 0,
            "total_time_spent_minutes": 0,
            "total_coins_earned": 0,
            "average_quiz_score": 0,
            "best_quiz_accuracy": 0,
            "recent_quizzes": [],
            "accuracy_trend": []
        }
    
    total = len(quizzes.data)
    total_questions = sum(q.get("total_questions", 0) for q in quizzes.data)
    overall_accuracy = sum(q.get("accuracy", 0) for q in quizzes.data) / total if total > 0 else 0
    total_time = sum(q.get("time_spent_minutes", 0) for q in quizzes.data)
    total_coins = sum(q.get("coins_earned", 0) for q in quizzes.data)
    best_accuracy = max(q.get("accuracy", 0) for q in quizzes.data)
    
    # Recent quizzes (last 5)
    recent = sorted(quizzes.data, key=lambda x: x.get("completed_at", ""), reverse=True)[:5]
    
    # Accuracy trend (last 10)
    trend_data = sorted(quizzes.data, key=lambda x: x.get("completed_at", ""))[-10:]
    accuracy_trend = [
        {"quiz_number": i+1, "accuracy": q.get("accuracy", 0)}
        for i, q in enumerate(trend_data)
    ]
    
    return {
        "total_quizzes": total,
        "total_questions_attempted": total_questions,
        "overall_accuracy": round(overall_accuracy, 2),
        "total_time_spent_minutes": round(total_time, 2),
        "total_coins_earned": total_coins,
        "average_quiz_score": round(overall_accuracy, 2),
        "best_quiz_accuracy": round(best_accuracy, 2),
        "recent_quizzes": recent,
        "accuracy_trend": accuracy_trend
    }