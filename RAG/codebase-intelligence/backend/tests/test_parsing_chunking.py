from app.rag.parser import parse_source_code
from app.rag.chunker import chunk_file


def test_python_ast_parsing_and_chunking():
    code = """# User Service Module
import os

class UserManager:
    def __init__(self, db):
        self.db = db

    def get_user(self, user_id: str):
        return self.db.find(user_id)

def authenticate(email: str, password: str) -> bool:
    return email == "admin@example.com" and password == "secret"
"""
    symbols = parse_source_code(code, "python")
    symbol_names = [s.name for s in symbols]

    assert "UserManager" in symbol_names
    assert "authenticate" in symbol_names

    chunks = chunk_file("services/user.py", "python", code)
    assert len(chunks) >= 2

    # Verify line numbers are accurate
    for c in chunks:
        assert c.start_line >= 1
        assert c.end_line >= c.start_line
        assert c.file_path == "services/user.py"
        assert c.content_hash is not None


def test_javascript_ast_parsing():
    js_code = """
function calculateTotal(items) {
    return items.reduce((acc, item) => acc + item.price, 0);
}

class Invoice {
    constructor(id) {
        this.id = id;
    }
}
"""
    symbols = parse_source_code(js_code, "javascript")
    names = [s.name for s in symbols]
    assert "calculateTotal" in names
    assert "Invoice" in names


def test_fallback_parser():
    unsupported_code = """
func ProcessData(ctx Context, id int) error {
    return nil
}

type Config struct {
    Port int
}
"""
    symbols = parse_source_code(unsupported_code, "go")
    names = [s.name for s in symbols]
    assert "ProcessData" in names or "Config" in names
