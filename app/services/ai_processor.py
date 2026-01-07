"""
AI Processor - Smart Hybrid Mode
Uses web scraping + AI for 10x faster processing
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx

from app.services.ai_service import StructureAI
from app.services.gpt_generator import GPTContentGenerator
from app.services.content_service import ContentService
from app.db.supabase import supabase

logger = logging.getLogger(__name__)


class AIProcessor:
    """Production-grade AI content processor with Smart Hybrid mode."""

    @staticmethod
    async def process_material(material_id: str):
        """Main processing pipeline."""
        try:
            logger.info(f"Starting GPT-4o-mini processing for {material_id}")
            
            # Step 1: Update status
            await AIProcessor._update_status(material_id, "extracting")
            
            # Step 2: Get material
            material = await AIProcessor._get_material(material_id)
            if not material:
                raise Exception("Material not found")
            
            # Step 3: Download and extract PDF
            logger.info(f"Downloading PDF from {material['file_url']}")
            pdf_text = await AIProcessor._download_pdf(material['file_url'])
            logger.info(f"Extracted {len(pdf_text)} characters")
            
            # Step 4: Extract structure with GPT
            logger.info("Extracting structure with GPT-4o-mini...")
            structure = await StructureAI.extract(pdf_text)
            logger.info(f"Extracted {len(structure['chapters'])} chapters")
            
            # Step 5: Store structure
            await AIProcessor._store_structure(material_id, structure)
            
            # Step 6: GPT GENERATION (Chapter-level)
            await AIProcessor._update_status(material_id, "generating")
            await AIProcessor._generate_gpt(material_id, structure)
            
            # Step 7: Mark as completed
            await AIProcessor._update_status(material_id, "completed")
            logger.info(f"✅ GPT-4o-mini processing completed for {material_id}")
            
        except Exception as e:
            logger.error(f"❌ Processing failed for {material_id}", exc_info=True)
            await AIProcessor._update_status(material_id, "failed", str(e)[:500])

    # ================================================================
    # SMART HYBRID GENERATION (NEW!)
    # ================================================================

    @staticmethod
    async def _generate_gpt(material_id: str, structure: Dict[str, Any]):
        """
        Generate content using Smart Hybrid approach.
        
        Per chapter:
        - Scrape MCQs & PYQs from web (2 min)
        - AI generates study materials (3 min)
        - AI fills gaps (2 min)
        
        Total: ~7 minutes per chapter vs 25 minutes (pure AI)
        """
        try:
            board = structure["detected_board"]
            class_ = structure["detected_class"]
            subject = structure["detected_subject"]
            
            # Get chapters from database
            chapters_db = supabase.table("chapters").select("*").eq(
                "material_id", material_id
            ).order("chapter_number").execute()
            
            if not chapters_db.data:
                logger.warning("No chapters found in database")
                return
            
            total_chapters = len(chapters_db.data)
            logger.info(f"🚀 GPT-4o-mini mode: Processing {total_chapters} chapters")
            
            for idx, chapter in enumerate(chapters_db.data, 1):
                chapter_id = chapter["id"]
                chapter_name = chapter["chapter_name"]
                
                # Get topics for this chapter
                topics_db = supabase.table("topics").select("*").eq(
                    "chapter_id", chapter_id
                ).execute()
                
                if not topics_db.data:
                    logger.info(f"No topics for chapter {chapter_name}, skipping")
                    continue
                
                logger.info(f"📚 Chapter {idx}/{total_chapters}: {chapter_name}")
                
                # GPT GENERATION (Fast & cheap!)
                result = await GPTContentGenerator.generate_complete_content(
                    chapter_id=chapter_id,
                    chapter_name=chapter_name,
                    topics=topics_db.data,
                    board=board,
                    class_=class_,
                    subject=subject,
                    material_id=material_id
                )
                
                logger.info(f"✅ Chapter {idx} complete: Generated with GPT-4o-mini")
                
                # Small delay between chapters
                if idx < total_chapters:
                    await asyncio.sleep(1)
            
            logger.info("✅ GPT generation completed for all chapters")
            
        except Exception as e:
            logger.error("Smart Hybrid generation failed", exc_info=True)
            raise

    # ================================================================
    # STRUCTURE STORAGE (Same as before)
    # ================================================================

    @staticmethod
    async def _store_structure(material_id: str, structure: Dict[str, Any]):
        """Store chapters and topics."""
        try:
            # Update material metadata
            supabase.table("uploaded_materials").update({
                "detected_class": structure["detected_class"],
                "detected_board": structure["detected_board"],
                "detected_subject": structure["detected_subject"],
                "chapters_extracted": len(structure["chapters"]),
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", material_id).execute()
            
            chapters_stored = 0
            topics_stored = 0
            
            for chapter in structure["chapters"]:
                try:
                    # Check if chapter exists
                    existing = supabase.table("chapters").select("id").eq(
                        "material_id", material_id
                    ).eq("chapter_number", chapter["chapter_number"]).execute()
                    
                    if existing.data:
                        chapter_id = existing.data[0]["id"]
                    else:
                        # Insert chapter
                        result = supabase.table("chapters").insert({
                            "id": str(uuid.uuid4()),
                            "material_id": material_id,
                            "chapter_number": chapter["chapter_number"],
                            "chapter_name": chapter["chapter_name"],
                            "chapter_description": chapter.get("description", ""),
                            "board": structure["detected_board"],
                            "created_at": datetime.utcnow().isoformat()
                        }).execute()
                        
                        chapter_id = result.data[0]["id"]
                        chapters_stored += 1
                    
                    # Store topics
                    for topic in chapter.get("topics", []):
                        try:
                            topic_name = topic.get("name", "") if isinstance(topic, dict) else str(topic)
                            if not topic_name or len(topic_name) < 3:
                                continue
                            
                            difficulty = topic.get("difficulty", "medium") if isinstance(topic, dict) else "medium"
                            if difficulty not in ["easy", "medium", "hard"]:
                                difficulty = "medium"
                            
                            # Check if topic exists
                            existing_topic = supabase.table("topics").select("id").eq(
                                "chapter_id", chapter_id
                            ).eq("topic_name", topic_name).execute()
                            
                            if not existing_topic.data:
                                supabase.table("topics").insert({
                                    "id": str(uuid.uuid4()),
                                    "chapter_id": chapter_id,
                                    "topic_name": topic_name,
                                    "topic_description": topic.get("description", ""),
                                    "difficulty_level": difficulty,
                                    "created_at": datetime.utcnow().isoformat()
                                }).execute()
                                
                                topics_stored += 1
                        
                        except Exception as e:
                            logger.warning(f"Failed to store topic: {str(e)[:100]}")
                            continue
                
                except Exception as e:
                    logger.error(f"Failed to store chapter: {str(e)[:100]}")
                    continue
            
            logger.info(f"✅ Stored {chapters_stored} chapters, {topics_stored} topics")
            
        except Exception as e:
            logger.error("Failed to store structure", exc_info=True)
            raise

    # ================================================================
    # HELPERS
    # ================================================================

    @staticmethod
    async def _get_material(material_id: str) -> Optional[Dict]:
        """Get material from database."""
        try:
            result = supabase.table("uploaded_materials").select("*").eq(
                "id", material_id
            ).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get material: {str(e)}")
            return None

    @staticmethod
    async def _download_pdf(url: str) -> str:
        """Download PDF and extract text."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return ContentService.extract_text_from_pdf(response.content)
        except Exception as e:
            logger.error(f"Failed to download PDF: {str(e)}")
            raise

    @staticmethod
    async def _update_status(material_id: str, status: str, error: Optional[str] = None):
        """Update processing status."""
        try:
            supabase.table("uploaded_materials").update({
                "processing_status": status,
                "error_message": error,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", material_id).execute()
            
            logger.info(f"Status updated to: {status}")
        except Exception as e:
            logger.error(f"Failed to update status: {str(e)}")


# ================================================================
# ENTRY POINT
# ================================================================

async def trigger_processing(material_id: str):
    """Trigger Smart Hybrid processing."""
    await AIProcessor.process_material(material_id)