"""
GPT-Powered Content Generator
Uses OpenAI GPT-4o-mini for all content generation
$5 = 50+ full books processed!
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Any
from openai import AsyncOpenAI

from app.core.config import settings
from app.db.supabase import supabase

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class GPTContentGenerator:
    """Pure GPT content generation - fast, cheap, no rate limits!"""
    
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
        """Generate all content for a chapter using GPT."""
        try:
            logger.info(f"📚 GPT generating content for: {chapter_name}")
            
            topics_text = ", ".join([t.get("topic_name", "") for t in topics[:10]])
            
            # Generate all content types sequentially
            concept = await GPTContentGenerator._generate_concept(chapter_name, topics_text)
            cheatsheet = await GPTContentGenerator._generate_cheatsheet(chapter_name, topics_text)
            flashcards = await GPTContentGenerator._generate_flashcards(chapter_name, topics_text)
            
            mcqs_easy = await GPTContentGenerator._generate_mcqs(chapter_name, board, class_, "easy")
            mcqs_medium = await GPTContentGenerator._generate_mcqs(chapter_name, board, class_, "medium")
            mcqs_hard = await GPTContentGenerator._generate_mcqs(chapter_name, board, class_, "hard")
            
            input_questions = await GPTContentGenerator._generate_input_questions(chapter_name, board, class_)
            
            # Store everything
            await GPTContentGenerator._store_all(
                material_id, chapter_id, topics,
                concept, cheatsheet, flashcards,
                mcqs_easy, mcqs_medium, mcqs_hard,
                input_questions, board, subject
            )
            
            logger.info(f"✅ GPT generation complete for {chapter_name}")
            
            return {
                "chapter_name": chapter_name,
                "generated": True,
                "model": "gpt-4o-mini"
            }
            
        except Exception as e:
            logger.error(f"GPT generation failed for {chapter_name}", exc_info=True)
            return {"chapter_name": chapter_name, "generated": False, "error": str(e)}
    
    # ================================================================
    # GENERATION METHODS
    # ================================================================
    
    @staticmethod
    async def _generate_concept(chapter_name: str, topics: str) -> Dict:
        """Generate concept explanation with GPT."""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert CBSE Economics teacher. Generate comprehensive concept explanations."
                    },
                    {
                        "role": "user",
                        "content": f"""Create a detailed concept explanation for:

Chapter: {chapter_name}
Topics: {topics}

Return ONLY valid JSON:
{{
  "explanation": "Comprehensive 3-4 paragraph explanation",
  "key_points": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
  "examples": ["Real-world example 1", "Real-world example 2"]
}}"""
                    }
                ]
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Concept generation failed: {str(e)[:100]}")
            return {}
    
    @staticmethod
    async def _generate_cheatsheet(chapter_name: str, topics: str) -> Dict:
        """Generate quick reference cheatsheet."""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.5,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Create concise, exam-focused cheatsheets for CBSE students."
                    },
                    {
                        "role": "user",
                        "content": f"""Create a one-page cheatsheet for:

Chapter: {chapter_name}
Topics: {topics}

Return ONLY valid JSON:
{{
  "points": [
    "Key formula/concept 1",
    "Key formula/concept 2",
    "Key formula/concept 3",
    "Key formula/concept 4",
    "Key formula/concept 5",
    "Key formula/concept 6",
    "Key formula/concept 7",
    "Key formula/concept 8"
  ]
}}"""
                    }
                ]
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Cheatsheet generation failed: {str(e)[:100]}")
            return {}
    
    @staticmethod
    async def _generate_flashcards(chapter_name: str, topics: str) -> List:
        """Generate flashcards for active recall."""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.6,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": "Create effective flashcards for spaced repetition learning."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 20 flashcards for:

Chapter: {chapter_name}
Topics: {topics}

Return ONLY valid JSON:
{{
  "flashcards": [
    {{
      "front": "Question or term",
      "back": "Answer or definition",
      "hint": "Memory aid (optional)"
    }}
  ]
}}"""
                    }
                ]
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("flashcards", [])
        except Exception as e:
            logger.error(f"Flashcard generation failed: {str(e)[:100]}")
            return []
    
    @staticmethod
    async def _generate_mcqs(chapter_name: str, board: str, class_: str, difficulty: str) -> List:
        """Generate MCQs at specified difficulty."""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a {board} board exam question paper setter. Create high-quality MCQs."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 15 {difficulty} difficulty MCQs for:

Chapter: {chapter_name}
Board: {board}
Class: {class_}
Difficulty: {difficulty}

Requirements:
- All 4 options must be plausible
- Only ONE correct answer
- Clear explanations
- Board exam style

Return ONLY valid JSON:
{{
  "mcqs": [
    {{
      "question_text": "Question text",
      "options": [
        {{"key": "A", "text": "Option A"}},
        {{"key": "B", "text": "Option B"}},
        {{"key": "C", "text": "Option C"}},
        {{"key": "D", "text": "Option D"}}
      ],
      "correct_answer": "A",
      "explanation": "Why A is correct",
      "difficulty": "{difficulty}",
      "marks": 1
    }}
  ]
}}"""
                    }
                ]
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("mcqs", [])
        except Exception as e:
            logger.error(f"MCQ generation failed ({difficulty}): {str(e)[:100]}")
            return []
    
    @staticmethod
    async def _generate_input_questions(chapter_name: str, board: str, class_: str) -> List:
        """Generate written board exam questions."""
        try:
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0.7,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"Create {board} board exam written questions with model answers."
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 10 written exam questions for:

Chapter: {chapter_name}
Board: {board}
Class: {class_}

Mix of:
- 2-3 mark short questions
- 4-6 mark long questions

Return ONLY valid JSON:
{{
  "questions": [
    {{
      "question": "Question text",
      "marks": 3,
      "answer": "Model answer",
      "type": "short"
    }}
  ]
}}"""
                    }
                ]
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
        except Exception as e:
            logger.error(f"Input questions generation failed: {str(e)[:100]}")
            return []
    
    # ================================================================
    # STORAGE
    # ================================================================
    
    @staticmethod
    async def _store_all(
        material_id: str,
        chapter_id: str,
        topics: List[Dict],
        concept: Dict,
        cheatsheet: Dict,
        flashcards: List,
        mcqs_easy: List,
        mcqs_medium: List,
        mcqs_hard: List,
        input_questions: List,
        board: str,
        subject: str
    ):
        """Store all generated content."""
        try:
            topic_id = topics[0]["id"] if topics else None
            
            # Store concept
            if concept:
                supabase.table("ai_generated_content").insert({
                    "id": str(uuid.uuid4()),
                    "material_id": material_id,
                    "chapter_id": chapter_id,
                    "topic_id": topic_id,
                    "content_type": "concept",
                    "content": concept,
                    "board": board,
                    "subject": subject,
                    "generated_by_ai": "gpt-4o-mini",
                    "validation_status": "approved"
                }).execute()
            
            # Store cheatsheet
            if cheatsheet:
                supabase.table("ai_generated_content").insert({
                    "id": str(uuid.uuid4()),
                    "material_id": material_id,
                    "chapter_id": chapter_id,
                    "topic_id": topic_id,
                    "content_type": "cheatsheet",
                    "content": cheatsheet,
                    "board": board,
                    "subject": subject,
                    "generated_by_ai": "gpt-4o-mini",
                    "validation_status": "approved"
                }).execute()
            
            # Store flashcards
            if flashcards:
                supabase.table("ai_generated_content").insert({
                    "id": str(uuid.uuid4()),
                    "material_id": material_id,
                    "chapter_id": chapter_id,
                    "topic_id": topic_id,
                    "content_type": "flashcard",
                    "content": flashcards,
                    "board": board,
                    "subject": subject,
                    "generated_by_ai": "gpt-4o-mini",
                    "validation_status": "approved"
                }).execute()
            
            # Store MCQs
            for difficulty, mcqs in [("easy", mcqs_easy), ("medium", mcqs_medium), ("hard", mcqs_hard)]:
                if mcqs:
                    supabase.table("ai_generated_content").insert({
                        "id": str(uuid.uuid4()),
                        "material_id": material_id,
                        "chapter_id": chapter_id,
                        "topic_id": topic_id,
                        "content_type": f"mcq_{difficulty}",
                        "content": mcqs,
                        "difficulty_level": difficulty,
                        "board": board,
                        "subject": subject,
                        "generated_by_ai": "gpt-4o-mini",
                        "validation_status": "approved"
                    }).execute()
            
            # Store input questions
            if input_questions:
                supabase.table("ai_generated_content").insert({
                    "id": str(uuid.uuid4()),
                    "material_id": material_id,
                    "chapter_id": chapter_id,
                    "topic_id": topic_id,
                    "content_type": "input",
                    "content": input_questions,
                    "board": board,
                    "subject": subject,
                    "generated_by_ai": "gpt-4o-mini",
                    "validation_status": "approved"
                }).execute()
            
            logger.info("✅ All content stored successfully")
            
        except Exception as e:
            logger.error(f"Storage failed: {str(e)}")