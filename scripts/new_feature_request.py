from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
REQUESTS_DIR = ROOT / "requests"
TEMPLATE_PATH = REQUESTS_DIR / "_template" / "feature_request.md"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "feature-request"


def build_body(args: argparse.Namespace) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    today = datetime.utcnow().date().isoformat()
    return (
        template.replace("<short title>", args.title)
        .replace("<name/team>", args.requested_by)
        .replace("<YYYY-MM-DD>", today)
        .replace("<models|products|engine|io|tests|docs>", args.area)
        .replace("<low|medium|high>", args.priority)
        .replace(
            "Describe the problem and why it matters.",
            args.details or "Describe the problem and why it matters.",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new feature request markdown file.")
    parser.add_argument("--title", required=True, help="Short feature title")
    parser.add_argument("--requested-by", default="unknown", help="Person or team requesting the feature")
    parser.add_argument("--area", default="engine", help="Feature area (models/products/engine/io/tests/docs)")
    parser.add_argument("--priority", default="medium", help="Priority (low/medium/high)")
    parser.add_argument("--details", default="", help="Optional problem statement")
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    short_id = uuid4().hex[:8]
    filename = f"{timestamp}-{slugify(args.title)}-{short_id}.md"
    output_path = REQUESTS_DIR / filename

    output_path.write_text(build_body(args), encoding="utf-8")
    print(output_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
