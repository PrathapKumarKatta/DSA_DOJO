from dataclasses import dataclass
import hashlib
from typing import List, Optional
from app.rag.parser import parse_source_code

MAX_CHUNK_LINES = 80
OVERLAP_LINES = 15


@dataclass
class CodeChunkData:
    file_path: str
    language: str
    symbol_name: Optional[str]
    chunk_type: str  # function, class, module, block
    start_line: int
    end_line: int
    content: str
    content_hash: str


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _split_large_block(
    file_path: str,
    language: str,
    symbol_name: Optional[str],
    chunk_type: str,
    content_lines: List[str],
    base_start_line: int,
) -> List[CodeChunkData]:
    """Break large function/block into bounded chunks while preserving exact line numbers."""
    chunks: List[CodeChunkData] = []
    total_lines = len(content_lines)
    i = 0

    while i < total_lines:
        chunk_lines = content_lines[i : i + MAX_CHUNK_LINES]
        chunk_text = "\n".join(chunk_lines).strip()
        if chunk_text:
            start_line = base_start_line + i
            end_line = start_line + len(chunk_lines) - 1
            chunks.append(
                CodeChunkData(
                    file_path=file_path,
                    language=language,
                    symbol_name=symbol_name,
                    chunk_type=chunk_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_text,
                    content_hash=compute_content_hash(chunk_text),
                )
            )

        if i + MAX_CHUNK_LINES >= total_lines:
            break
        i += MAX_CHUNK_LINES - OVERLAP_LINES

    return chunks


def chunk_file(file_path: str, language: str, content: str) -> List[CodeChunkData]:
    """
    Intelligently chunk a source file using AST symbols for code and line-bounded
    structural windows for configuration/documentation.
    """
    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return []

    # For structured code languages: attempt AST symbol parsing first
    code_languages = {"python", "javascript", "typescript", "java", "c", "cpp"}
    if language in code_languages:
        symbols = parse_source_code(content, language)
        if symbols:
            chunks: List[CodeChunkData] = []
            covered_lines = set()

            # 1. First capture module header (imports, docstrings, configs before first symbol)
            first_sym_line = min(s.start_line for s in symbols)
            if first_sym_line > 1:
                header_lines = lines[: first_sym_line - 1]
                header_text = "\n".join(header_lines).strip()
                if header_text:
                    chunks.append(
                        CodeChunkData(
                            file_path=file_path,
                            language=language,
                            symbol_name=None,
                            chunk_type="module",
                            start_line=1,
                            end_line=first_sym_line - 1,
                            content=header_text,
                            content_hash=compute_content_hash(header_text),
                        )
                    )
                    covered_lines.update(range(1, first_sym_line))

            # 2. Add each symbol chunk
            for sym in symbols:
                sym_line_count = sym.end_line - sym.start_line + 1
                if sym_line_count <= MAX_CHUNK_LINES:
                    chunks.append(
                        CodeChunkData(
                            file_path=file_path,
                            language=language,
                            symbol_name=sym.name,
                            chunk_type=sym.symbol_type,
                            start_line=sym.start_line,
                            end_line=sym.end_line,
                            content=sym.content.strip(),
                            content_hash=compute_content_hash(sym.content),
                        )
                    )
                else:
                    # Large function / class: split into bounded chunks
                    sym_lines = lines[sym.start_line - 1 : sym.end_line]
                    sub_chunks = _split_large_block(
                        file_path=file_path,
                        language=language,
                        symbol_name=sym.name,
                        chunk_type=sym.symbol_type,
                        content_lines=sym_lines,
                        base_start_line=sym.start_line,
                    )
                    chunks.extend(sub_chunks)

                covered_lines.update(range(sym.start_line, sym.end_line + 1))

            if chunks:
                return chunks

    # Small files (<= 40 lines) without symbols: single module chunk
    if total_lines <= 40:
        return [
            CodeChunkData(
                file_path=file_path,
                language=language,
                symbol_name=None,
                chunk_type="module",
                start_line=1,
                end_line=total_lines,
                content=content.strip(),
                content_hash=compute_content_hash(content),
            )
        ]

    # Fallback / non-code languages (Markdown, JSON, text, or files without identifiable symbols)
    return _split_large_block(
        file_path=file_path,
        language=language,
        symbol_name=None,
        chunk_type="block",
        content_lines=lines,
        base_start_line=1,
    )
