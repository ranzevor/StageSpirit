import json
from pathlib import Path
from xml.etree import ElementTree

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "contracts/schemas"
SCHEMA_FILES = sorted(SCHEMAS.glob("*.schema.json"))
REGISTRY = Registry().with_resources(
    (path.as_uri(), Resource.from_contents(json.loads(path.read_text("utf-8"))))
    for path in SCHEMA_FILES
)
EXAMPLE_TARGETS = {
    "event": "live-event",
    "error": "common#/$defs/Error",
    "operation-receipt": "common#/$defs/OperationReceipt",
    "resource-receipt": "common#/$defs/ResourceReceipt",
    "stage-apply-result": "stage-output#/$defs/StageApplyResult",
    "stage-output-release": "stage-output#/$defs/StageOutputRelease",
}


def validator(target: str) -> Draft202012Validator:
    name, _, fragment = target.partition("#")
    uri = (SCHEMAS / f"{name}.schema.json").as_uri()
    if fragment:
        uri += f"#{fragment}"
    return Draft202012Validator({"$ref": uri}, registry=REGISTRY, format_checker=FormatChecker())


def example_target(path: Path) -> str:
    candidates = {
        schema.name.removesuffix(".schema.json"): schema.name.removesuffix(".schema.json")
        for schema in SCHEMA_FILES
    }
    candidates.update(EXAMPLE_TARGETS)
    matches = [name for name in candidates if path.stem == name or path.stem.startswith(name + "-")]
    if not matches:
        raise ValueError(f"Missing schema for {path.name}")
    return candidates[max(matches, key=len)]


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_schema_is_valid(path: Path) -> None:
    Draft202012Validator.check_schema(json.loads(path.read_text("utf-8")))


@pytest.mark.parametrize(
    "path", sorted((ROOT / "examples/contracts").glob("*.json")), ids=lambda path: path.name
)
def test_valid_example(path: Path) -> None:
    validator(example_target(path)).validate(json.loads(path.read_text("utf-8")))


@pytest.mark.parametrize(
    "path",
    sorted((ROOT / "tests/fixtures/contracts").rglob("invalid/*.json")),
    ids=lambda path: str(path.relative_to(ROOT / "tests/fixtures/contracts")),
)
def test_invalid_example(path: Path) -> None:
    parts = path.relative_to(ROOT / "tests/fixtures/contracts").parts
    target = parts[0]
    if len(parts) == 4:
        target += f"#/$defs/{parts[1]}"
    assert not validator(target).is_valid(json.loads(path.read_text("utf-8")))


def test_brand_svg_is_well_formed() -> None:
    svg = ElementTree.parse(ROOT / "docs/assets/stagespirit.svg").getroot()
    assert svg.tag == "{http://www.w3.org/2000/svg}svg"
    for tag in ("title", "desc"):
        child = svg.find(f"{{http://www.w3.org/2000/svg}}{tag}")
        assert child is not None and child.text and child.text.strip()


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_schema_references_resolve_locally(path: Path) -> None:
    pending = [json.loads(path.read_text("utf-8"))]
    resolver = REGISTRY.resolver(path.as_uri())
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            if "$ref" in value:
                assert not value["$ref"].startswith(("http:", "https:"))
                resolver.lookup(value["$ref"])
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def test_tool_catalog_paging_mutations_and_schema_links() -> None:
    path = ROOT / "contracts/tool-catalog.json"
    catalog = json.loads(path.read_text("utf-8"))
    tools = catalog["tools"]
    assert len({tool["name"] for tool in tools}) == len(tools)
    assert catalog["pagination"] == {"default_limit": 50, "max_limit": 200}
    resolver = REGISTRY.resolver(path.as_uri())
    for tool in tools:
        if tool["kind"] == "command":
            assert "data_generation" in tool["input"], tool["name"]
        if tool.get("paged"):
            assert {"limit", "cursor"}.issubset(tool["input"]), tool["name"]
        for field in ("input_schema", "output_schema"):
            if field in tool:
                resolver.lookup(tool[field])
