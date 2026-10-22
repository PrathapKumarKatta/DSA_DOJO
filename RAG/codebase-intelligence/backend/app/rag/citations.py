import re
from typing import List, Optional
from app.schemas.chat import CitationResponse
from app.schemas.search import SearchResultChunk


def extract_and_validate_citations(
    llm_answer: str,
    retrieved_chunks: List[SearchResultChunk],
) -> List[CitationResponse]:
    """
    Extract cited files and line numbers from model output, and validate them
    strictly against the candidate chunks retrieved from the project.
    Prevents hallucinated files or IDs.
    """
    citations: List[CitationResponse] = []
    seen = set()

    # Pattern: [File: path/to/file | Lines: 12–34] or [File: path/to/file:12-34]
    pattern = re.compile(
        r"\[File:\s*([^\s\]|]+)(?:\s*\|\s*Lines:\s*(\d+)[–\-](\d+))?\]",
        re.IGNORECASE,
    )

    matches = pattern.findall(llm_answer)

    for match in matches:
        file_path = match[0].strip()
        start_line = int(match[1]) if match[1] else None
        end_line = int(match[2]) if match[2] else None

        # Check against retrieved chunks to bind real chunk_id
        matched_chunk: Optional[SearchResultChunk] = None
        for chunk in retrieved_chunks:
            if chunk.file_path == file_path:
                if start_line is not None and end_line is not None:
                    # Check overlap
                    if not (end_line < chunk.start_line or start_line > chunk.end_line):
                        matched_chunk = chunk
                        break
                else:
                    matched_chunk = chunk
                    break

        if matched_chunk:
            key = (matched_chunk.file_path, matched_chunk.start_line, matched_chunk.end_line)
            if key not in seen:
                seen.add(key)
                citations.append(
                    CitationResponse(
                        chunk_id=matched_chunk.chunk_id,
                        file_path=matched_chunk.file_path,
                        start_line=matched_chunk.start_line,
                        end_line=matched_chunk.end_line,
                        snippet=matched_chunk.content[:200],
                    )
                )

    # If the LLM did not include standard bracket tags but answered based on retrieved chunks,
    # attach the top retrieved chunks as authoritative citations.
    if not citations and retrieved_chunks:
        for chunk in retrieved_chunks[:3]:
            key = (chunk.file_path, chunk.start_line, chunk.end_line)
            if key not in seen:
                seen.add(key)
                citations.append(
                    CitationResponse(
                        chunk_id=chunk.chunk_id,
                        file_path=chunk.file_path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        snippet=chunk.content[:200],
                    )
                )

    return citations
