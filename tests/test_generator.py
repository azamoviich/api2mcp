import ast
import json

import pytest

from api2mcp.generator import render_server, write_server
from api2mcp.parser import parse_spec

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Order API"},
    "servers": [{"url": "https://api.example.com"}],
    "paths": {
        "/orders/{orderId}": {
            "delete": {
                "operationId": "deleteOrder",
                "parameters": [
                    {"name": "apiKey", "in": "header", "required": False, "schema": {"type": "string"}},
                    {"name": "orderId", "in": "path", "required": True, "schema": {"type": "integer"}},
                ],
            }
        }
    },
}


@pytest.fixture
def spec_file(tmp_path):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(SPEC))
    return str(p)


def test_generated_code_is_valid_python(spec_file):
    spec = parse_spec(spec_file)
    code = render_server(spec)
    ast.parse(code)  # raises SyntaxError if invalid


def test_required_params_ordered_before_optional(spec_file):
    """Regression: optional param (apiKey) appears before required (orderId) in
    the raw OpenAPI param list, but Python needs required args first."""
    spec = parse_spec(spec_file)
    code = render_server(spec)
    ast.parse(code)
    assert "def deleteorder(orderId: int, apiKey: str = \"\")" in code


def test_write_server_creates_files(tmp_path, spec_file):
    spec = parse_spec(spec_file)
    server_file = write_server(spec, str(tmp_path / "out"))
    assert server_file.exists()
    assert (tmp_path / "out" / "README.md").exists()
    ast.parse(server_file.read_text())
