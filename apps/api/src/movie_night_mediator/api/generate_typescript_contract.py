from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from movie_night_mediator.api.main import create_app


DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[5] / "apps" / "web" / "app" / "api-contract.generated.ts"
)
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def render_typescript_contract() -> str:
    schema = create_app().openapi()
    component_schemas = schema.get("components", {}).get("schemas", {})
    lines = [
        "// Generated from FastAPI OpenAPI components.",
        "// Do not edit by hand. Regenerate with:",
        "// cd apps/api && ../../.tools/uv/bin/uv run python -m movie_night_mediator.api.generate_typescript_contract",
        "",
    ]

    for schema_name in sorted(component_schemas):
        rendered = _render_schema(component_schemas[schema_name], indent_level=0)
        lines.append(f"export type {schema_name} = {rendered};")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_typescript_contract(output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_typescript_contract(), encoding="utf-8")
    return output_path


def _render_schema(schema: dict[str, Any], *, indent_level: int) -> str:
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return reference.rsplit("/", 1)[-1]

    if "enum" in schema:
        return " | ".join(_literal(value) for value in schema["enum"])

    if "const" in schema:
        return _literal(schema["const"])

    any_of = schema.get("anyOf")
    if isinstance(any_of, list) and any_of:
        return " | ".join(
            _render_schema(option, indent_level=indent_level) for option in any_of
        )

    one_of = schema.get("oneOf")
    if isinstance(one_of, list) and one_of:
        return " | ".join(
            _render_schema(option, indent_level=indent_level) for option in one_of
        )

    all_of = schema.get("allOf")
    if isinstance(all_of, list) and all_of:
        return " & ".join(
            _render_schema(option, indent_level=indent_level) for option in all_of
        )

    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema or "additionalProperties" in schema:
        return _render_object_schema(schema, indent_level=indent_level)

    if schema_type == "array":
        items = schema.get("items", {})
        return f"{_wrap_array_member(_render_schema(items, indent_level=indent_level))}[]"

    if schema_type == "string":
        return "string"

    if schema_type in {"integer", "number"}:
        return "number"

    if schema_type == "boolean":
        return "boolean"

    if schema_type == "null":
        return "null"

    return "unknown"


def _render_object_schema(schema: dict[str, Any], *, indent_level: int) -> str:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    additional_properties = schema.get("additionalProperties")
    lines: list[str] = ["{"]

    if isinstance(properties, dict):
        for property_name in sorted(properties):
            property_schema = properties[property_name]
            optional_suffix = "" if property_name in required else "?"
            rendered_property = _render_schema(
                property_schema, indent_level=indent_level + 1
            )
            lines.append(
                f"{_indent(indent_level + 1)}{_property_name(property_name)}{optional_suffix}: {rendered_property};"
            )

    if additional_properties is True:
        lines.append(f"{_indent(indent_level + 1)}[key: string]: unknown;")
    elif isinstance(additional_properties, dict):
        lines.append(
            f"{_indent(indent_level + 1)}[key: string]: {_render_schema(additional_properties, indent_level=indent_level + 1)};"
        )

    if len(lines) == 1:
        return "Record<string, unknown>"

    lines.append(f"{_indent(indent_level)}}}")
    return "\n".join(lines)


def _wrap_array_member(rendered: str) -> str:
    if "\n" in rendered or "|" in rendered or "&" in rendered:
        return f"({rendered})"

    return rendered


def _property_name(name: str) -> str:
    if IDENTIFIER_PATTERN.match(name):
        return name

    return json.dumps(name)


def _literal(value: Any) -> str:
    return json.dumps(value)


def _indent(indent_level: int) -> str:
    return "  " * indent_level


if __name__ == "__main__":
    output_path = write_typescript_contract()
    print(output_path)
