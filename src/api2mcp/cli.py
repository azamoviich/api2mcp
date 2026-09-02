from __future__ import annotations

import argparse
import sys

from .generator import write_server
from .parser import parse_spec


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="api2mcp",
        description="Turn any OpenAPI spec into a working MCP server.",
    )
    parser.add_argument("source", help="OpenAPI spec URL or local file path (json or yaml)")
    parser.add_argument("-o", "--out", default="./mcp_server", help="Output directory (default: ./mcp_server)")
    args = parser.parse_args()

    print(f"Fetching spec from {args.source} ...")
    try:
        spec = parse_spec(args.source)
    except Exception as exc:  # noqa: BLE001
        print(f"error: failed to parse spec: {exc}", file=sys.stderr)
        sys.exit(1)

    if not spec.operations:
        print("error: no operations found in spec", file=sys.stderr)
        sys.exit(1)

    out_file = write_server(spec, args.out)
    print(f"Generated {len(spec.operations)} tools for '{spec.title}'")
    print(f"-> {out_file}")
    print(f"-> {out_file.parent / 'README.md'}")
    print("\nRun it:")
    print(f'  cd {args.out} && pip install "mcp[cli]" requests && python server.py')


if __name__ == "__main__":
    main()
