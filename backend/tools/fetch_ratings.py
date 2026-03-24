from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings


OUTPUT_DIR = BACKEND_DIR / "ratings_export"


def _save_json(filename: str, payload: Any) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / filename).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _extract_matches(obj: Any, terms: list[str], path: str = "$", matches: list[dict] | None = None) -> list[dict]:
    if matches is None:
        matches = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            value_lower = value.lower() if isinstance(value, str) else ""
            if any(term in key_lower for term in terms) or (
                isinstance(value, str) and any(term in value_lower for term in terms)
            ):
                matches.append({"path": f"{path}.{key}", "key": key, "value": value})
            _extract_matches(value, terms, f"{path}.{key}", matches)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _extract_matches(item, terms, f"{path}[{index}]", matches)

    return matches


def _iter_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "feedbacks", "ratings"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return [payload]


def _pick(record: dict, *paths: str) -> Any:
    for path in paths:
        current: Any = record
        ok = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                ok = False
                break
        if ok and current is not None:
            return current
    return None


def _summarize_endpoint(name: str, payload: Any) -> dict[str, Any]:
    terms = [
        "course",
        "module",
        "teacher",
        "instructor",
        "staffedteacher",
        "rating",
        "feedback",
        "prompt",
        "answered",
        "comment",
    ]
    records = _iter_records(payload)
    sample_rows = []
    for record in records[:10]:
        if not isinstance(record, dict):
            sample_rows.append({"value": record})
            continue
        sample_rows.append(
            {
                "id": _pick(record, "id", "rating_id", "feedback_id", "prompt_id"),
                "answered": _pick(record, "answered", "is_answered", "status"),
                "rating": _pick(record, "rating", "score", "value"),
                "comment": _pick(record, "comment", "feedback", "text"),
                "course": _pick(
                    record,
                    "course.name",
                    "course_module.course_module_name",
                    "course_module_name",
                    "module_name",
                    "courseModule.name",
                ),
                "teacher": _pick(
                    record,
                    "teacher.name",
                    "teacher_name",
                    "instructor.name",
                    "staffed_teacher.teacher_name",
                ),
            }
        )

    return {
        "endpoint": name,
        "record_count": len(records),
        "top_level_type": type(payload).__name__,
        "top_level_keys": list(payload.keys())[:30] if isinstance(payload, dict) else None,
        "interesting_matches": _extract_matches(payload, terms)[:60],
        "sample_rows": sample_rows,
    }


def main() -> None:
    settings = get_settings()
    if not settings.albert_base_url or not settings.albert_bearer_token:
        raise SystemExit("Albert API settings missing in backend/.env")

    headers = {
        "Authorization": f"Bearer {settings.albert_bearer_token}",
        "Accept": "application/json",
    }

    with httpx.Client(base_url=settings.albert_base_url, headers=headers, timeout=30.0) as client:
        profile = client.get("/user/user-profile")
        profile.raise_for_status()
        profile_payload = profile.json()
        user_id = profile_payload["user_id"]

        endpoints = {
            "rating_by_user": f"/rating/by-user-id/{user_id}?page=1&limit=50&answered=false",
            "user_feedbacks": "/feedback/get-user-feedbacks",
            "feedback_prompt_history": "/feedback-prompt-history/",
        }

        summaries = []
        for name, endpoint in endpoints.items():
            response = client.get(endpoint)
            payload: Any
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw_text": response.text}

            wrapper = {
                "endpoint": endpoint,
                "status_code": response.status_code,
                "payload": payload,
            }
            _save_json(f"{name}.json", wrapper)
            summaries.append(_summarize_endpoint(name, payload))

    _save_json("summary.json", summaries)

    print("Ratings export complete.")
    print(f"Output dir: {OUTPUT_DIR}")
    for summary in summaries:
        print()
        print(summary["endpoint"])
        print(f"  record_count: {summary['record_count']}")
        print(f"  top_level_keys: {summary['top_level_keys']}")
        for row in summary["sample_rows"][:5]:
            print(f"  sample: {row}")


if __name__ == "__main__":
    main()
