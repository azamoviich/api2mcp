"""Loads an OpenAPI spec and flattens it into a list of Operation objects."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

PY_TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


@dataclass
class Param:
    name: str
    location: str  # "path" | "query" | "header" | "body"
    py_type: str = "str"
    required: bool = False
    description: str = ""


@dataclass
class Operation:
    op_id: str
    method: str
    path: str
    summary: str = ""
    params: list[Param] = field(default_factory=list)

    @property
    def func_name(self) -> str:
        name = re.sub(r"[^a-zA-Z0-9]+", "_", self.op_id).strip("_").lower()
        return name or f"{self.method}_{self.path}".lower()


@dataclass
class ApiSpec:
    title: str
    base_url: str
    operations: list[Operation]


def _load_raw(source: str) -> dict:
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        resp = requests.get(source, timeout=15)
        resp.raise_for_status()
        text = resp.text
    else:
        text = Path(source).read_text()

    text_stripped = text.lstrip()
    if text_stripped.startswith("{"):
        return json.loads(text)
    return yaml.safe_load(text)


def _resolve_type(schema: dict | None) -> str:
    if not schema:
        return "str"
    return PY_TYPE_MAP.get(schema.get("type"), "str")


def _base_url(raw: dict, source: str) -> str:
    parsed_source = urlparse(source)
    source_origin = (
        f"{parsed_source.scheme}://{parsed_source.netloc}"
        if parsed_source.scheme in ("http", "https")
        else None
    )

    servers = raw.get("servers") or []
    if servers and servers[0].get("url"):
        url = servers[0]["url"]
        if url.startswith("http"):
            return url
        if url.startswith("/") and source_origin:
            return source_origin.rstrip("/") + url

    return source_origin or "http://localhost:8000"


def parse_spec(source: str) -> ApiSpec:
    raw = _load_raw(source)
    title = (raw.get("info") or {}).get("title", "API")
    base_url = _base_url(raw, source)

    operations: list[Operation] = []
    paths = raw.get("paths") or {}
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            op_id = op.get("operationId") or f"{method}_{path}"
            params: list[Param] = []

            for p in op.get("parameters", []):
                schema = p.get("schema") or {}
                params.append(
                    Param(
                        name=p["name"],
                        location=p.get("in", "query"),
                        py_type=_resolve_type(schema),
                        required=p.get("required", False),
                        description=p.get("description", ""),
                    )
                )

            body = op.get("requestBody")
            if body:
                content = body.get("content", {})
                json_schema = (content.get("application/json") or {}).get("schema", {})
                props = json_schema.get("properties", {})
                required_fields = set(json_schema.get("required", []))
                if props:
                    for pname, pschema in props.items():
                        params.append(
                            Param(
                                name=pname,
                                location="body",
                                py_type=_resolve_type(pschema),
                                required=pname in required_fields,
                                description=pschema.get("description", ""),
                            )
                        )
                else:
                    params.append(Param(name="body", location="body", py_type="dict", required=True))

            operations.append(
                Operation(
                    op_id=op_id,
                    method=method.lower(),
                    path=path,
                    summary=op.get("summary", "") or op.get("description", ""),
                    params=params,
                )
            )

    return ApiSpec(title=title, base_url=base_url, operations=operations)
