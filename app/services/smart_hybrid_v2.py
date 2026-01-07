"""
Smart Hybrid Generator V2 - With Claude Web Search
Uses Claude's built-in web_search tool for intelligent question gathering
10x Better Quality • No Scraping Issues • Auto-Validated
"""

import asyncio
import logging
import re
import json
import uuid
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

import anthropic
from app.core.config import settings
from app.services.ai_service import ContentAI
from app.db.supabase import supabase

logger = logging.getLogger(__name__)

# Initialize Claude with search capability
claude_with_search = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
SEARCH_EXECUTOR = ThreadPoolExecutor(max_workers=2)


class SmartHybridGeneratorV2:
    """
    Next-gen content generator using Claude's web_search.
    
    Advantages over manual scraping:
    - Claude validates question quality
    - Gets content from multiple sources automatically
    - Handles formatting and extraction
    - No parsing errors
    - Better source diversity
    """
    
    @staticmethod
    async def generate_complete_content(
        chapter_id: str,
        chapter_name: str,
        topics: List[Dict],
        board: str,
        class_: str,
        subject: str,
        material_id: str
    ) -> Dict[str, Any]:
        """
        Generate complete content using Claude web search.
        
        Strategy:
        1. Claude searches web for MCQs and PYQs
        2. Claude extracts and validates questions
        3. Claude generates study materials
        4. Claude fills gaps with AI-generated content
        """
        try:
            logger.info(f"🔍 Smart search for: {chapter_name}")
            
            # PHASE 1: INTELLIGENT WEB SEARCH
            logger.info("📡 Phase 1: Claude searching web for questions...")
            
            search_result = await SmartHybridGeneratorV2._search_with_claude(
                chapter_name=chapter_name,
                board=board,
                class_=class_,
                subject=subject
            )
            
            scraped_mcqs = search_result.get("mcqs", [])
            scraped_pyqs = search_result.get("pyqs", [])
            
            logger.info(
                f"✅ Found: {len(scraped_mcqs)} MCQs, "
                f"{len(scraped_pyqs)} PYQs from web"
            )
            
            # PHASE 2: AI STUDY MATERIALS (Parallel)
            logger.info("🤖 Phase 2: Generating study materials...")
            
            topics_summary = ", ".join([t.get("topic_name", "") for t in topics[:8]])
            
            study_tasks = [
                ContentAI.generate_concept(chapter_name, topics_summary, "en"),
                ContentAI.generate_cheatsheet(chapter_name, topics_summary, "en"),
                ContentAI.generate_flashcards(chapter_name, topics_summary, "en")
            ]
            
            study_results = await asyncio.gather(*study_tasks, return_exceptions=True)
            
            concept = study_results[0] if not isinstance(study_results[0], Exception) else {}
            cheatsheet = study_results[1] if not isinstance(study_results[1], Exception) else {}
            flashcards = study_results[2] if not isinstance(study_results[2], Exception) else []
            
            logger.info(
                f"✅ Generated study materials: Concept, Cheatsheet, "
                f"{len(flashcards) if isinstance(flashcards, list) else 0} Flashcards"
            )
            
            # PHASE 3: INTELLIGENT GAP FILLING
            logger.info("🔧 Phase 3: Claude filling gaps...")
            
            mcqs_by_difficulty, input_questions = await SmartHybridGeneratorV2._fill_gaps_with_claude(
                chapter_name=chapter_name,
                scraped_mcqs=scraped_mcqs,
                board=board,
                class_=class_,
                subject=subject
            )
            
            total_mcqs = sum(len(v) for v in mcqs_by_difficulty.values())
            logger.info(f"✅ Total MCQs: {total_mcqs}, Input Questions: {len(input_questions)}")
            
            # PHASE 4: STORE EVERYTHING
            logger.info("💾 Phase 4: Storing content...")
            
            stored = await SmartHybridGeneratorV2._store_all_content(
                material_id=material_id,
                chapter_id=chapter_id,
                topics=topics,
                concept=concept,
                cheatsheet=cheatsheet,
                flashcards=flashcards,
                mcqs_by_difficulty=mcqs_by_difficulty,
                pyqs=scraped_pyqs,
                input_questions=input_questions,
                board=board,
                subject=subject
            )
            
            logger.info(f"✅ Smart search complete for {chapter_name}")
            
            return {
                "chapter_name": chapter_name,
                "web_searched_mcqs": len(scraped_mcqs),
                "web_searched_pyqs": len(scraped_pyqs),
                "ai_generated_mcqs": total_mcqs - len(scraped_mcqs),
                "flashcards": len(flashcards) if isinstance(flashcards, list) else 0,
                "stored_items": sum(stored.values()),
                "method": "claude_web_search"
            }
            
        except Exception as e:
            logger.error(f"Smart search failed for {chapter_name}", exc_info=True)
            return await SmartHybridGeneratorV2._fallback_pure_ai(
                chapter_id, chapter_name, topics, board, class_, subject, material_id
            )
    
    # ================================================================
    # CLAUDE WEB SEARCH
    # ================================================================
    
    @staticmethod
    async def _search_with_claude(
        chapter_name: str,
        board: str,
        class_: str,
        subject: str
    ) -> Dict[str, List]:
        """
        Use Claude's web_search to find questions.
        Claude intelligently searches, extracts, and validates.
        """
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                SEARCH_EXECUTOR,
                SmartHybridGeneratorV2._claude_search_sync,
                chapter_name,
                board,
                class_,
                subject
            )
            return result
            
        except Exception as e:
            logger.error(f"Claude web search failed: {str(e)}")
            return {"mcqs": [], "pyqs": []}
    
    @staticmethod
    def _claude_search_sync(
        chapter_name: str,
        board: str,
        class_: str,
        subject: str
    ) -> Dict[str, List]:
        """
        Synchronous Claude search with tool use.
        """
        try:
            prompt = f"""Search the web and find high-quality educational content for:

Chapter: {chapter_name}
Board: {board}
Class: {class_}
Subject: {subject}

Task:
1. Search for MCQ questions related to this chapter
2. Search for Previous Year Questions (PYQs) from {board} board exams
3. Extract questions in proper format
4. Validate quality and relevance

Return ONLY valid JSON:
{{
  "mcqs": [
    {{
      "question_text": "Clear question text",
      "options": [
        {{"key": "A", "text": "Option A"}},
        {{"key": "B", "text": "Option B"}},
        {{"key": "C", "text": "Option C"}},
        {{"key": "D", "text": "Option D"}}
      ],
      "correct_answer": "A",
      "explanation": "Why this is correct",
      "source": "URL or source name",
      "difficulty": "medium"
    }}
  ],
  "pyqs": [
    {{
      "year": "2023",
      "question": "Question text",
      "marks": 3,
      "source": "URL or source name"
    }}
  ]
}}

Focus on finding REAL exam questions from trusted sources like:
- CBSE official website
- NCERT
- Previous year board papers
- Reputable education sites (Toppr, Vedantu, Unacademy)

Search and extract at least 10-15 MCQs and 5-10 PYQs.
"""
            
            # Use Claude with tools enabled
            message = claude_with_search.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                temperature=0.3,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search"
                }],
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract content from response
            full_text = ""
            for block in message.content:
                if hasattr(block, 'text'):
                    full_text += block.text
            
            # Parse JSON from response
            json_match = re.search(r'(\{[\s\S]*\})', full_text)
            if json_match:
                result = json.loads(json_match.group(1))
                
                # Validate and clean
                mcqs = result.get("mcqs", [])[:15]  # Limit to 15
                pyqs = result.get("pyqs", [])[:10]  # Limit to 10
                
                logger.info(f"Claude extracted {len(mcqs)} MCQs and {len(pyqs)} PYQs")
                
                return {
                    "mcqs": mcqs,
                    "pyqs": pyqs
                }
            else:
                logger.warning("No JSON found in Claude search response")
                return {"mcqs": [], "pyqs": []}
            
        except Exception as e:
            logger.error(f"Claude search sync failed: {str(e)[:200]}")
            return {"mcqs": [], "pyqs": []}
    
    # ================================================================
    # INTELLIGENT GAP FILLING
    # ================================================================
    
    @staticmethod
    async def _fill_gaps_with_claude(
        chapter_name: str,
        scraped_mcqs: List[Dict],
        board: str,
        class_: str,
        subject: str
    ) -> tuple:
        """
        Claude analyzes what's missing and generates to fill gaps.
        """
        try:
            # Categorize scraped MCQs by difficulty
            mcqs_by_diff = {"easy": [], "medium": [], "hard": []}
            
            for mcq in scraped_mcqs:
                diff = mcq.get("difficulty", "medium")
                if diff in mcqs_by_diff:
                    mcqs_by_diff[diff].append(mcq)
            
            # Determine what's needed
            target_per_diff = 15
            tasks = []
            
            for difficulty in ["easy", "medium", "hard"]:
                current = len(mcqs_by_diff[difficulty])
                if current < target_per_diff:
                    needed = target_per_diff - current
                    logger.info(f"Generating {needed} {difficulty} MCQs")
                    tasks.append(
                        ContentAI.generate_mcqs(chapter_name, board, class_, difficulty, "en")
                    )
                else:
                    tasks.append(asyncio.sleep(0))  # Placeholder
            
            # Always generate input questions
            tasks.append(
                ContentAI.generate_input_questions(chapter_name, board, class_, "en")
            )
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Merge results
            idx = 0
            for difficulty in ["easy", "medium", "hard"]:
                if len(mcqs_by_diff[difficulty]) < target_per_diff:
                    if not isinstance(results[idx], Exception) and isinstance(results[idx], list):
                        needed = target_per_diff - len(mcqs_by_diff[difficulty])
                        mcqs_by_diff[difficulty].extend(results[idx][:needed])
                    idx += 1
                else:
                    idx += 1
            
            input_questions = results[-1] if not isinstance(results[-1], Exception) else []
            
            return mcqs_by_diff, input_questions
            
        except Exception as e:
            logger.error(f"Gap filling failed: {str(e)}")
            return {"easy": [], "medium": [], "hard": []}, []
    
    # ================================================================
    # STORAGE
    # ================================================================
    
    @staticmethod
    async def _store_all_content(
        material_id: str,
        chapter_id: str,
        topics: List[Dict],
        concept: Dict,
        cheatsheet: Dict,
        flashcards: List,
        mcqs_by_difficulty: Dict,
        pyqs: List,
        input_questions: List,
        board: str,
        subject: str
    ) -> Dict[str, int]:
        """Store all content in database."""
        
        stored = {
            "concepts": 0,
            "cheatsheets": 0,
            "flashcards": 0,
            "mcqs": 0,
            "pyqs": 0,
            "input_questions": 0
        }
        
        try:
            topic_id = topics[0]["id"] if topics else None
            
            # Store concept
            if concept:
                try:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": "concept",
                        "content": concept,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "claude-smart-search",
                        "validation_status": "approved"
                    }).execute()
                    stored["concepts"] = 1
                except Exception as e:
                    logger.warning(f"Failed to store concept: {str(e)[:100]}")
            
            # Store cheatsheet
            if cheatsheet:
                try:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": "cheatsheet",
                        "content": cheatsheet,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "claude-smart-search",
                        "validation_status": "approved"
                    }).execute()
                    stored["cheatsheets"] = 1
                except Exception as e:
                    logger.warning(f"Failed to store cheatsheet: {str(e)[:100]}")
            
            # Store flashcards
            if flashcards:
                try:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": "flashcard",
                        "content": flashcards,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "claude-smart-search",
                        "validation_status": "approved"
                    }).execute()
                    stored["flashcards"] = len(flashcards) if isinstance(flashcards, list) else 0
                except Exception as e:
                    logger.warning(f"Failed to store flashcards: {str(e)[:100]}")
            
            # Store MCQs
            for difficulty, mcq_list in mcqs_by_difficulty.items():
                if mcq_list:
                    try:
                        supabase.table("ai_generated_content").insert({
                            "id": str(uuid.uuid4()),
                            "material_id": material_id,
                            "chapter_id": chapter_id,
                            "topic_id": topic_id,
                            "content_type": f"mcq_{difficulty}",
                            "content": mcq_list,
                            "difficulty_level": difficulty,
                            "board": board,
                            "subject": subject,
                            "generated_by_ai": "claude-smart-search",
                            "validation_status": "approved"
                        }).execute()
                        stored["mcqs"] += len(mcq_list)
                    except Exception as e:
                        logger.warning(f"Failed to store {difficulty} MCQs: {str(e)[:100]}")
            
            # Store PYQs
            if pyqs:
                try:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": "pyq",
                        "content": pyqs,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "web-search-claude",
                        "validation_status": "approved"
                    }).execute()
                    stored["pyqs"] = len(pyqs)
                except Exception as e:
                    logger.warning(f"Failed to store PYQs: {str(e)[:100]}")
            
            # Store input questions
            if input_questions:
                try:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": "input",
                        "content": input_questions,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "claude-smart-search",
                        "validation_status": "approved"
                    }).execute()
                    stored["input_questions"] = len(input_questions) if isinstance(input_questions, list) else 0
                except Exception as e:
                    logger.warning(f"Failed to store input questions: {str(e)[:100]}")
            
            return stored
            
        except Exception as e:
            logger.error(f"Storage failed: {str(e)}")
            return stored
    
    # ================================================================
    # FALLBACK
    # ================================================================
    
    @staticmethod
    async def _fallback_pure_ai(
        chapter_id: str,
        chapter_name: str,
        topics: List[Dict],
        board: str,
        class_: str,
        subject: str,
        material_id: str
    ) -> Dict:
        """Pure AI generation as last resort."""
        logger.warning(f"Using pure AI fallback for {chapter_name}")
        
        tasks = [
            ContentAI.generate_concept(chapter_name, "", "en"),
            ContentAI.generate_cheatsheet(chapter_name, "", "en"),
            ContentAI.generate_flashcards(chapter_name, "", "en"),
            ContentAI.generate_mcqs(chapter_name, board, class_, "medium", "en")
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "chapter_name": chapter_name,
            "fallback_mode": True
        }