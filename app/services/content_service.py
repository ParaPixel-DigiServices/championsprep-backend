"""
Content Service - Handle material uploads and chapter management
"""

from typing import Optional, List, Dict, Any, Tuple
import uuid
from datetime import datetime
import io
import logging

from app.db.supabase import supabase
from app.core.errors import AIServiceError
import PyPDF2

logger = logging.getLogger(__name__)


class ContentService:
    """Handle material uploads and processing."""
    
    @staticmethod
    async def upload_material(
        file: io.BytesIO,
        filename: str,
        uploaded_by: str
    ) -> Dict[str, Any]:
        """Upload PDF material to Supabase storage."""
        try:
            # Validate file size (max 50MB)
            file.seek(0)
            file_bytes = file.read()
            file_size = len(file_bytes)
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                raise AIServiceError("File too large. Maximum size is 50MB")
            
            if file_size < 1024:  # 1KB
                raise AIServiceError("File too small. Minimum size is 1KB")
            
            # Validate PDF format
            try:
                PyPDF2.PdfReader(io.BytesIO(file_bytes))
            except Exception:
                raise AIServiceError("Invalid PDF file")
            
            # Generate unique filename
            material_id = str(uuid.uuid4())
            storage_filename = f"{material_id}_{filename}"
            
            # Upload to Supabase storage
            storage_path = f"uploads/{storage_filename}"
            
            try:
                supabase.storage.from_("study-materials").upload(
                    storage_path,
                    file_bytes,
                    {"content-type": "application/pdf"}
                )
            except Exception as e:
                logger.error(f"Storage upload failed: {str(e)}")
                raise AIServiceError("Failed to upload file to storage")
            
            # Get public URL
            file_url = supabase.storage.from_("study-materials").get_public_url(storage_path)
            
            # Create database record
            material_data = {
                "id": material_id,
                "filename": storage_filename,
                "original_filename": filename,
                "file_url": file_url,
                "file_size_bytes": file_size,
                "mime_type": "application/pdf",
                "uploaded_by": uploaded_by,
                "processing_status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = supabase.table("uploaded_materials").insert(material_data).execute()
            
            if not result.data:
                raise AIServiceError("Failed to create database record")
            
            logger.info(f"✅ Material uploaded: {material_id}")
            
            return {
                "id": material_id,
                "filename": filename,
                "file_url": file_url,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "processing_status": "pending",
                "message": "Material uploaded successfully"
            }
            
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}", exc_info=True)
            raise AIServiceError(f"Failed to upload material: {str(e)}")
    
    @staticmethod
    async def get_all_materials(
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """Get all uploaded materials with pagination."""
        try:
            query = supabase.table("uploaded_materials").select("*")
            
            if status:
                query = query.eq("processing_status", status)
            
            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            # Get total count
            count_query = supabase.table("uploaded_materials").select("id", count="exact")
            if status:
                count_query = count_query.eq("processing_status", status)
            count_result = count_query.execute()
            
            total = len(count_result.data) if count_result.data else 0
            
            return result.data or [], total
            
        except Exception as e:
            logger.error(f"Failed to get materials: {str(e)}")
            return [], 0
    
    @staticmethod
    async def get_processing_status(material_id: str) -> Dict[str, Any]:
        """Get processing status with calculated progress."""
        try:
            result = supabase.table("uploaded_materials").select("*").eq("id", material_id).execute()
            
            if not result.data:
                raise AIServiceError("Material not found")
            
            material = result.data[0]
            status = material.get("processing_status", "pending")
            
            # Calculate progress percentage
            progress_map = {
                "pending": 0,
                "extracting": 25,
                "generating": 50,
                "validating": 75,
                "completed": 100,
                "failed": 0
            }
            
            return {
                "material_id": material_id,
                "filename": material.get("original_filename", ""),
                "processing_status": status,
                "progress_percentage": progress_map.get(status, 0),
                "current_step": status.replace("_", " ").title(),
                "chapters_extracted": material.get("chapters_extracted", 0),
                "topics_extracted": material.get("topics_extracted", 0),
                "mcqs_generated": material.get("mcqs_generated", 0),
                "flashcards_generated": material.get("flashcards_generated", 0),
                "error_message": material.get("error_message"),
                "started_at": material.get("created_at"),
                "updated_at": material.get("updated_at")
            }
            
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}")
            raise AIServiceError(f"Failed to get processing status: {str(e)}")
    
    @staticmethod
    async def start_processing(material_id: str) -> bool:
        """Start/restart processing for a material."""
        try:
            # Verify material exists
            result = supabase.table("uploaded_materials").select("id").eq("id", material_id).execute()
            
            if not result.data:
                return False
            
            # Update status to pending
            supabase.table("uploaded_materials").update({
                "processing_status": "pending",
                "error_message": None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", material_id).execute()
            
            logger.info(f"Processing queued for material: {material_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start processing: {str(e)}")
            return False
    
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes.
        Note: This is SYNCHRONOUS (not async) because PyPDF2 is synchronous.
        """
        try:
            if not pdf_bytes or len(pdf_bytes) < 100:
                raise AIServiceError("Invalid PDF data")
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            if len(pdf_reader.pages) == 0:
                raise AIServiceError("PDF has no pages")
            
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {str(e)}")
                    continue
            
            text = text.strip()
            
            if not text or len(text) < 100:
                raise AIServiceError("No text content found in PDF")
            
            logger.info(f"✅ Extracted {len(text)} characters from {len(pdf_reader.pages)} pages")
            
            return text
            
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}", exc_info=True)
            raise AIServiceError(f"Failed to extract text from PDF: {str(e)}")


class ChapterService:
    """Handle chapters and topics queries."""
    
    @staticmethod
    async def get_chapters_by_subject(class_id: str, subject_id: str) -> List[Dict]:
        """Get chapters for a specific class and subject."""
        try:
            # For now, return all chapters (TODO: Add class/subject filtering)
            result = supabase.table("chapters").select("*").order("chapter_number").execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get chapters: {str(e)}")
            return []
    
    @staticmethod
    async def get_topics_by_chapter(chapter_id: str) -> List[Dict]:
        """Get all topics for a specific chapter."""
        try:
            result = supabase.table("topics").select("*").eq(
                "chapter_id", chapter_id
            ).order("display_order").execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Failed to get topics: {str(e)}")
            return []
    
    @staticmethod
    async def get_chapter_by_id(chapter_id: str) -> Optional[Dict]:
        """Get single chapter by ID."""
        try:
            result = supabase.table("chapters").select("*").eq("id", chapter_id).execute()
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to get chapter: {str(e)}")
            return None