"""Generate docs/spec.yml from the FastAPI app's own schema. CI artifact — never
hand-edit (spec 13). Run: uv run python scripts/export_openapi.py"""

import pathlib

import yaml

from app.main import app

out = pathlib.Path(__file__).resolve().parent.parent / "docs" / "spec.yml"
out.write_text(yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True), encoding="utf-8")
print(f"wrote {out}")
