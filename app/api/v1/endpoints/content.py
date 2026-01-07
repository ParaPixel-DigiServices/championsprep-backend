"""
Content management API endpoints.
Admin uploads PDFs, system processes them with AI.
"""

from fastapi import APIRouter, Depends, UploadFile, File, status, Query
from typing import Optional, List

from app.models.content import (
    MaterialUploadResponse,
    ProcessingStatusResponse,
    ChapterResponse,
    ChapterListResponse,
    TopicResponse,
    TopicListResponse,
)
from app.models.auth import UserResponse, MessageResponse
from app.services.content_service import ContentService, ChapterService
from app.api.v1.dependencies import require_admin, get_current_user
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/content", tags=["Content Management"])


# ============================================================================
# ADMIN - MATERIAL UPLOAD
# ============================================================================

@router.post(
    "/upload",
    response_model=MaterialUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload study material (Admin)",
    description="Upload PDF for AI processing and content extraction"
)
async def upload_material(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_admin)
) -> MaterialUploadResponse:
    """
    Upload study material PDF (Admin only).
    
    **Process:**
    1. Admin uploads PDF
    2. System stores in Supabase Storage
    3. AI extracts chapters, topics, content
    4. AI generates MCQs, flashcards, exams
    5. Gemini validates all content
    6. Content becomes available to students
    
    **File Requirements:**
    - Format: PDF only
    - Size: Max 50MB
    - Content: Educational textbook/material
    
    **What AI Extracts:**
    - Class/Grade level
    - Board (CBSE/ICSE/etc)
    - Subject
    - Chapters (exact names from book)
    - Topics & subtopics
    - Difficulty levels
    
    **What AI Generates:**
    - MCQs (Easy/Medium/Hard)
    - Flashcards
    - 3-hour board exam papers
    - Mind maps
    - Summaries
    
    **Requires:** Admin role
    """
    return await ContentService.upload_material(
        file=file.file,
        filename=file.filename,
        uploaded_by=current_user.id
    )


@router.get(
    "/materials",
    summary="List uploaded materials (Admin)",
    description="Get list of all uploaded materials with processing status"
)
async def list_materials(
    status: Optional[str] = Query(None, description="Filter by processing status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_admin)
):
    """
    Get list of uploaded materials (Admin only).
    
    **Query Parameters:**
    - `status`: Filter by processing status (pending, extracting, completed, failed)
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 20, max: 100)
    
    **Returns:**
    - List of materials with processing status
    - Upload details
    - Extraction results
    
    **Requires:** Admin role
    """
    offset = (page - 1) * page_size
    
    materials, total = await ContentService.get_all_materials(
        status=status,
        limit=page_size,
        offset=offset
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "materials": materials,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get(
    "/materials/{material_id}/status",
    response_model=ProcessingStatusResponse,
    summary="Get processing status",
    description="Check AI processing status of uploaded material"
)
async def get_material_status(
    material_id: str,
    current_user: UserResponse = Depends(require_admin)
) -> ProcessingStatusResponse:
    """
    Get processing status of uploaded material (Admin only).
    
    **Shows:**
    - Current processing stage (extracting/generating/validating)
    - Progress percentage
    - Chapters extracted
    - Topics extracted
    - Questions generated
    - Any errors
    
    **Processing Stages:**
    1. **Pending** - Queued for processing
    2. **Extracting** - AI extracting structure from PDF
    3. **Generating** - AI creating questions & content
    4. **Validating** - Gemini checking for accuracy
    5. **Completed** - Ready for students
    6. **Failed** - Error occurred
    
    **Requires:** Admin role
    """
    return await ContentService.get_processing_status(material_id)


@router.post(
    "/materials/{material_id}/process",
    response_model=MessageResponse,
    summary="Process material (Admin)",
    description="Manually trigger AI processing for uploaded material"
)
async def process_material(
    material_id: str,
    current_user: UserResponse = Depends(require_admin)
) -> MessageResponse:
    """
    Manually trigger AI processing for material (Admin only).
    
    **This starts the complete pipeline:**
    1. Extract text from PDF
    2. Claude extracts chapters & topics
    3. Gemini validates extraction
    4. Claude generates MCQs, flashcards, exams
    5. Gemini validates each question
    6. Store validated content
    
    **Use this to:**
    - Start processing after upload
    - Retry failed processing
    - Reprocess with updated AI models
    
    **Note:** Processing happens in background and may take several minutes.
    Use `/materials/{material_id}/status` to check progress.
    
    **Requires:** Admin role
    """
    from app.services.ai_processor import trigger_processing
    import asyncio
    
    # Start processing in background
    asyncio.create_task(trigger_processing(material_id))
    
    return MessageResponse(
        message="Processing started. Check status endpoint for progress.",
        success=True
    )


@router.post(
    "/materials/{material_id}/reprocess",
    response_model=MessageResponse,
    summary="Reprocess material (Admin)",
    description="Restart AI processing for failed material"
)
async def reprocess_material(
    material_id: str,
    current_user: UserResponse = Depends(require_admin)
) -> MessageResponse:
    """
    Restart processing for a failed material (Admin only).
    
    **Use when:**
    - Processing failed due to temporary error
    - Need to regenerate content
    - AI models improved
    
    **Requires:** Admin role
    """
    success = await ContentService.start_processing(material_id)
    
    if success:
        return MessageResponse(
            message="Processing restarted successfully",
            success=True
        )
    else:
        return MessageResponse(
            message="Failed to restart processing",
            success=False
        )


# ============================================================================
# STUDENT - BROWSE CONTENT
# ============================================================================

@router.get(
    "/chapters",
    response_model=ChapterListResponse,
    summary="Get chapters",
    description="Get all chapters for a subject"
)
async def get_chapters(
    class_id: str = Query(..., description="Class ID"),
    subject_id: str = Query(..., description="Subject ID"),
    current_user: UserResponse = Depends(get_current_user)
) -> ChapterListResponse:
    """
    Get all chapters for a subject.
    
    **Returns:**
    - Chapters extracted from textbooks
    - Exact chapter names as in book
    - Chapter descriptions
    - Validation status
    
    **Use for:**
    - Building subject navigation
    - Showing chapter list to students
    
    **Note:** Only validated chapters are shown
    
    **Requires:** Valid access token
    """
    chapters = await ChapterService.get_chapters_by_subject(
        class_id=class_id,
        subject_id=subject_id
    )
    
    return ChapterListResponse(
        chapters=[ChapterResponse(**ch) for ch in chapters],
        total=len(chapters)
    )


@router.get(
    "/chapters/{chapter_id}/topics",
    response_model=TopicListResponse,
    summary="Get topics for chapter",
    description="Get all topics and subtopics for a chapter"
)
async def get_chapter_topics(
    chapter_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> TopicListResponse:
    """
    Get all topics for a chapter.
    
    **Returns:**
    - Topics and subtopics
    - Difficulty levels
    - Topic descriptions
    
    **Hierarchy:**
    - Level 1: Main topics
    - Level 2: Subtopics
    - Level 3: Sub-subtopics
    
    **Use for:**
    - Building chapter navigation
    - Showing topic selection
    - Practice mode selection
    
    **Requires:** Valid access token
    """
    topics = await ChapterService.get_topics_by_chapter(chapter_id)
    
    return TopicListResponse(
        topics=[TopicResponse(**topic) for topic in topics],
        total=len(topics)
    )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get(
    "/stats",
    summary="Get content statistics (Admin)",
    description="Get overall content statistics"
)
async def get_content_stats(
    current_user: UserResponse = Depends(require_admin)
):
    """
    Get content statistics (Admin only).
    
    **Shows:**
    - Total materials uploaded
    - Processing success/failure rate
    - Total chapters extracted
    - Total questions generated
    - Coverage by class/subject
    
    **Requires:** Admin role
    """
    # TODO: Implement comprehensive stats
    
    return {
        "total_materials": 0,
        "processing_completed": 0,
        "processing_failed": 0,
        "total_chapters": 0,
        "total_topics": 0,
        "total_mcqs": 0,
        "total_flashcards": 0,
        "total_exams": 0
    }