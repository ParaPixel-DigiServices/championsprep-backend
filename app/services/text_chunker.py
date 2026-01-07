# app/services/text_chunker.py
from typing import List
import re

MAX_CHARS = 12000   # Safe for GLM-4.5

def smart_chunk_text(text: str) -> List[str]:
    """
    Splits textbook into logical readable chunks (not dumb slicing).
    Keeps paragraphs intact.
    """
    text = re.sub(r'\n{3,}', '\n\n', text)
    paragraphs = text.split("\n\n")

    chunks, current = [], ""

    for p in paragraphs:
        if len(current) + len(p) < MAX_CHARS:
            current += p + "\n\n"
        else:
            chunks.append(current.strip())
            current = p + "\n\n"

    if current.strip():
        chunks.append(current.strip())

    return chunks
