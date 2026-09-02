# api2mcp

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)

**Turn any OpenAPI spec into a working [MCP](https://modelcontextprotocol.io) server. One command.**

```bash
api2mcp https://petstore3.swagger.io/api/v3/openapi.json
```

That's it. You now have a runnable MCP server exposing every endpoint in that API as a tool an LLM agent can call — typed arguments, docstrings, auth wiring, all generated.

---

## The problem

Want Claude (or any MCP-compatible agent) to use Stripe, GitHub, your internal REST API, whatever? Right now that means hand-writing an MCP server: read the docs, define a tool per endpoint, map params, wire up auth, keep it in sync when the API changes.

Almost every API already publishes an OpenAPI/Swagger spec describing exactly that shape. `api2mcp` reads it and generates the server for you.

## Install

```bash
pip install spec2mcp
```

(The PyPI package is named `spec2mcp` — `api2mcp` was already taken. The CLI command and import name are still `api2mcp`.)

## Usage

```bash
api2mcp <spec-url-or-file> [-o output-dir]
```

Works with a spec URL, a local `.json` file, or a local `.yaml`/`.yml` file.

### Example

```bash
$ api2mcp https://petstore3.swagger.io/api/v3/openapi.json -o ./petstore-mcp
Fetching spec from https://petstore3.swagger.io/api/v3/openapi.json ...
Generated 19 tools for 'Swagger Petstore - OpenAPI 3.0'
-> petstore-mcp/server.py
-> petstore-mcp/README.md

Run it:
  cd petstore-mcp && pip install "mcp[cli]" requests && python server.py
```

Run the generated server, then point any MCP client at it — Claude Desktop, Claude Code, or your own agent — and every endpoint (`findPetsByStatus`, `addPet`, `deletePet`, …) is now a callable tool.

### Point Claude Desktop / Claude Code at it

Add to your MCP client config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "petstore": {
      "command": "python",
      "args": ["/absolute/path/to/petstore-mcp/server.py"],
      "env": {
        "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
        "API_KEY": "your-key-if-needed"
      }
    }
  }
}
```

### Auth

Set env vars before running the generated server:

- `API_BASE_URL` — overrides the base URL detected from the spec
- `API_KEY` — sent as `Authorization: Bearer <API_KEY>` on every request

### Use it as a library instead of the CLI

```python
from api2mcp import parse_spec, write_server

spec = parse_spec("https://petstore3.swagger.io/api/v3/openapi.json")
write_server(spec, "./out")
```

## What gets generated

For every operation in the spec, one `@mcp.tool()`-decorated function:

```python
@mcp.tool()
def findpetsbystatus(status: str = "") -> dict:
    """Finds Pets by status."""
    ...
    resp = requests.request("GET", url, params=params, json=json_body, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json()
```

- Path, query, and JSON body params become typed Python arguments (required params ordered before optional ones, so it's always valid Python)
- The `summary`/`description` from the spec becomes the tool's docstring — that's what the LLM sees when deciding whether to call it
- A `README.md` listing every generated tool ships alongside `server.py`

The output is plain, readable code — not a black box. Generate it, read it, edit it by hand if you need something custom.

## How it works

1. **Parse** (`api2mcp/parser.py`) — loads the spec (JSON or YAML, URL or file), walks `paths`, flattens each operation's parameters and request body into a simple typed `Operation` model.
2. **Generate** (`api2mcp/generator.py` + `templates/server.py.j2`) — renders a Jinja2 template into a single-file MCP server using the official `mcp` Python SDK.
3. **Run** — the generated server is a normal Python script; `mcp.run()` speaks the MCP protocol over stdio.

No LLM calls involved in generation — it's pure codegen from the spec's structure, so it's fast, free, and deterministic.

## Development

```bash
git clone https://github.com/azamoviich/api2mcp
cd api2mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,serve]"
pytest
```

## Limitations (v1)

- No OAuth2 flows — only static bearer token auth via `API_KEY`
- `$ref` resolution for request bodies is shallow (one level)
- No pagination helpers — generated tools return raw responses as-is

Contributions welcome for any of the above.

## License

MIT — see [LICENSE](LICENSE).
