import json
import textwrap

import pytest

from api2mcp.parser import parse_spec

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API"},
    "servers": [{"url": "/v1"}],
    "paths": {
        "/pets/{petId}": {
            "get": {
                "operationId": "getPet",
                "summary": "Get a pet",
                "parameters": [
                    {"name": "petId", "in": "path", "required": True, "schema": {"type": "integer"}},
                    {"name": "verbose", "in": "query", "required": False, "schema": {"type": "boolean"}},
                ],
            }
        },
        "/pets": {
            "post": {
                "operationId": "createPet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "age": {"type": "integer"},
                                },
                            }
                        }
                    }
                },
            }
        },
    },
}


@pytest.fixture
def spec_file(tmp_path):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(SPEC))
    return str(p)


def test_parse_spec_basic(spec_file):
    spec = parse_spec(spec_file)
    assert spec.title == "Test API"
    assert len(spec.operations) == 2


def test_base_url_joins_relative_server_with_source_origin(monkeypatch, tmp_path):
    """Regression: a relative `servers[].url` (e.g. "/api/v3") must be joined
    with the spec source's origin, not silently dropped."""
    import api2mcp.parser as parser_mod

    monkeypatch.setattr(parser_mod, "_load_raw", lambda source: SPEC)
    spec = parser_mod.parse_spec("https://example.com/openapi.json")
    assert spec.base_url == "https://example.com/v1"


def test_path_and_query_params(spec_file):
    spec = parse_spec(spec_file)
    op = next(o for o in spec.operations if o.op_id == "getPet")
    assert op.method == "get"
    locs = {p.name: p.location for p in op.params}
    assert locs["petId"] == "path"
    assert locs["verbose"] == "query"
    required = {p.name: p.required for p in op.params}
    assert required["petId"] is True
    assert required["verbose"] is False


def test_body_params_flattened(spec_file):
    spec = parse_spec(spec_file)
    op = next(o for o in spec.operations if o.op_id == "createPet")
    body_params = {p.name: p for p in op.params if p.location == "body"}
    assert body_params["name"].required is True
    assert body_params["age"].required is False
    assert body_params["age"].py_type == "int"


def test_func_name_sanitized(spec_file):
    spec = parse_spec(spec_file)
    op = next(o for o in spec.operations if o.op_id == "getPet")
    assert op.func_name == "getpet"
