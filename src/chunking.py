"""
Chunking Module – Vector DB Explorer
Text chunking utilities demonstrating different chunking strategies
as covered in Milestone 5: text chunking & embedding.
"""

import re
from typing import List, Dict


def chunk_by_sentences(text: str, sentences_per_chunk: int = 3) -> List[Dict]:
    """
    Chunk text by grouping sentences.

    Args:
        text: Input text.
        sentences_per_chunk: Number of sentences per chunk.

    Returns:
        List of chunk dictionaries.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []

    for i in range(0, len(sentences), sentences_per_chunk):
        group = sentences[i:i + sentences_per_chunk]
        chunk_text = ' '.join(group).strip()
        if chunk_text:
            chunks.append({
                "id": f"sent_chunk_{len(chunks)}",
                "text": chunk_text,
                "method": "sentence",
                "char_count": len(chunk_text),
                "sentence_count": len(group)
            })

    return chunks


def chunk_by_characters(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Chunk text by character count with overlap.

    Args:
        text: Input text.
        chunk_size: Target characters per chunk.
        overlap: Overlap characters between chunks.

    Returns:
        List of chunk dictionaries.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append({
                "id": f"char_chunk_{len(chunks)}",
                "text": chunk_text,
                "method": "character",
                "char_count": len(chunk_text),
                "start_pos": start,
                "end_pos": min(end, len(text))
            })

        start = end - overlap
        if start >= len(text):
            break

    return chunks


def chunk_by_paragraphs(text: str) -> List[Dict]:
    """
    Chunk text by paragraphs (double newline separation).

    Args:
        text: Input text.

    Returns:
        List of chunk dictionaries.
    """
    paragraphs = re.split(r'\n\s*\n', text.strip())
    chunks = []

    for para in paragraphs:
        para = para.strip()
        if para and len(para) > 20:  # Skip very short fragments
            chunks.append({
                "id": f"para_chunk_{len(chunks)}",
                "text": para,
                "method": "paragraph",
                "char_count": len(para)
            })

    return chunks


def chunk_by_words(text: str, words_per_chunk: int = 100, overlap_words: int = 10) -> List[Dict]:
    """
    Chunk text by word count with overlap.

    Args:
        text: Input text.
        words_per_chunk: Target words per chunk.
        overlap_words: Overlap words between chunks.

    Returns:
        List of chunk dictionaries.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + words_per_chunk
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words).strip()

        if chunk_text:
            chunks.append({
                "id": f"word_chunk_{len(chunks)}",
                "text": chunk_text,
                "method": "word",
                "char_count": len(chunk_text),
                "word_count": len(chunk_words)
            })

        start = end - overlap_words
        if start >= len(words):
            break

    return chunks


def chunk_text(text: str, method: str = "sentence", **kwargs) -> List[Dict]:
    """
    Chunk text using the specified method.

    Args:
        text: Input text.
        method: Chunking method ('sentence', 'character', 'paragraph', 'word').
        **kwargs: Additional arguments for the chunking method.

    Returns:
        List of chunk dictionaries.
    """
    methods = {
        "sentence": chunk_by_sentences,
        "character": chunk_by_characters,
        "paragraph": chunk_by_paragraphs,
        "word": chunk_by_words
    }

    if method not in methods:
        raise ValueError(f"Unknown method '{method}'. Choose from: {list(methods.keys())}")

    return methods[method](text, **kwargs)


def get_chunking_stats(chunks: List[Dict]) -> Dict:
    """
    Calculate statistics for a set of chunks.

    Args:
        chunks: List of chunk dictionaries.

    Returns:
        Statistics dictionary.
    """
    if not chunks:
        return {"total_chunks": 0}

    char_counts = [c["char_count"] for c in chunks]

    return {
        "total_chunks": len(chunks),
        "total_characters": sum(char_counts),
        "avg_chunk_size": round(sum(char_counts) / len(char_counts), 1),
        "min_chunk_size": min(char_counts),
        "max_chunk_size": max(char_counts),
        "method": chunks[0].get("method", "unknown")
    }
