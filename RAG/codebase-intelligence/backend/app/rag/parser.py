from dataclasses import dataclass
from typing import Dict, List, Optional
import re
from app.core.logging import logger

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_java
    import tree_sitter_c
    import tree_sitter_cpp

    PARSERS: Dict[str, Parser] = {
        "python": Parser(Language(tree_sitter_python.language())),
        "javascript": Parser(Language(tree_sitter_javascript.language())),
        "typescript": Parser(Language(tree_sitter_typescript.language_typescript())),
        "java": Parser(Language(tree_sitter_java.language())),
        "c": Parser(Language(tree_sitter_c.language())),
        "cpp": Parser(Language(tree_sitter_cpp.language())),
    }
except Exception as e:
    logger.warning(f"Tree-sitter initialization warning: {e}. Fallback parser will be active.")
    PARSERS = {}


@dataclass
class CodeSymbol:
    name: str
    symbol_type: str  # function, class, method, module
    start_line: int   # 1-indexed
    end_line: int     # 1-indexed
    content: str


def _get_node_name(node, source_bytes: bytes) -> Optional[str]:
    """Helper to extract the identifier name child node."""
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")
    return None


def parse_with_treesitter(content: str, language: str) -> List[CodeSymbol]:
    """Parse source code AST using Tree-sitter."""
    parser = PARSERS.get(language)
    if not parser:
        return []

    source_bytes = content.encode("utf-8")
    tree = parser.parse(source_bytes)
    symbols: List[CodeSymbol] = []

    def visit(node):
        node_type = node.type
        name = None
        symbol_type = None

        if language == "python":
            if node_type == "function_definition":
                name = _get_node_name(node, source_bytes)
                symbol_type = "function"
            elif node_type == "class_definition":
                name = _get_node_name(node, source_bytes)
                symbol_type = "class"

        elif language in ("javascript", "typescript"):
            if node_type in ("function_declaration", "function_expression"):
                name = _get_node_name(node, source_bytes) or "anonymous_function"
                symbol_type = "function"
            elif node_type == "class_declaration":
                name = _get_node_name(node, source_bytes)
                symbol_type = "class"
            elif node_type == "method_definition":
                name = _get_node_name(node, source_bytes)
                symbol_type = "method"
            elif node_type == "variable_declarator":
                # Check for arrow function
                for child in node.children:
                    if child.type == "arrow_function":
                        name = _get_node_name(node, source_bytes)
                        symbol_type = "function"

        elif language == "java":
            if node_type in ("method_declaration", "constructor_declaration"):
                name = _get_node_name(node, source_bytes)
                symbol_type = "function"
            elif node_type == "class_declaration":
                name = _get_node_name(node, source_bytes)
                symbol_type = "class"

        elif language in ("c", "cpp"):
            if node_type == "function_definition":
                # Declarator holds the name
                for child in node.children:
                    if child.type in ("function_declarator", "declarator"):
                        name = _get_node_name(child, source_bytes)
                symbol_type = "function"
            elif node_type in ("class_specifier", "struct_specifier"):
                name = _get_node_name(node, source_bytes)
                symbol_type = "class"

        if name and symbol_type:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            node_text = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            symbols.append(
                CodeSymbol(
                    name=name,
                    symbol_type=symbol_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=node_text,
                )
            )

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return symbols


def parse_fallback(content: str, language: str) -> List[CodeSymbol]:
    """Fallback parser using regex heuristics when AST parsing is unavailable."""
    lines = content.splitlines()
    symbols: List[CodeSymbol] = []

    # Patterns for def/class/function/struct
    func_pattern = re.compile(r"^\s*(?:async\s+)?(?:def|function|fn|func|public\s+\w+|private\s+\w+)\s+([a-zA-Z0-9_]+)")
    class_pattern = re.compile(r"^\s*(?:class|struct|interface)\s+([a-zA-Z0-9_]+)")

    current_symbol: Optional[Dict] = None

    for idx, line in enumerate(lines):
        line_num = idx + 1
        class_match = class_pattern.match(line)
        func_match = func_pattern.match(line)

        if class_match or func_match:
            if current_symbol:
                current_symbol["end_line"] = line_num - 1
                current_symbol["content"] = "\n".join(
                    lines[current_symbol["start_line"] - 1 : current_symbol["end_line"]]
                )
                symbols.append(CodeSymbol(**current_symbol))
                current_symbol = None

            if class_match:
                current_symbol = {
                    "name": class_match.group(1),
                    "symbol_type": "class",
                    "start_line": line_num,
                    "end_line": line_num,
                    "content": "",
                }
            elif func_match:
                current_symbol = {
                    "name": func_match.group(1),
                    "symbol_type": "function",
                    "start_line": line_num,
                    "end_line": line_num,
                    "content": "",
                }

    if current_symbol:
        current_symbol["end_line"] = len(lines)
        current_symbol["content"] = "\n".join(
            lines[current_symbol["start_line"] - 1 : current_symbol["end_line"]]
        )
        symbols.append(CodeSymbol(**current_symbol))

    return symbols


def parse_source_code(content: str, language: str) -> List[CodeSymbol]:
    """
    Primary code parsing entrypoint.
    Attempts AST parse first; falls back to regex parser if empty or failed.
    """
    if language in PARSERS:
        try:
            ast_symbols = parse_with_treesitter(content, language)
            if ast_symbols:
                return ast_symbols
        except Exception as e:
            logger.debug(f"AST parsing failed for {language}: {e}. Using fallback parser.")

    return parse_fallback(content, language)
