#!/usr/bin/env python3
"""Capture exact raw bytes for a prospective GMLI Money Core vintage.

This script is intentionally fail-closed. It does not transform data, run the
frozen research tests, or modify lib/state.js. Its only job is to preserve
source bytes and provenance so a future promotion run can be reproduced.
"""

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "prospective-money-source-manifest.json"
CAPTURE_ROOT = ROOT / "research" / "prospective-inputs"
AUDIT_ROOT = ROOT / "audit"
USER_AGENT = "GMLI-prospective-capture/1.0"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_vintage(value: str) -> str:
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", value):
        raise ValueError("Vintage must be YYYY-MM")
    return value


def safe_filename(value: str) -> str:
    name = pathlib.PurePath(value).name
    if not name or name != value or name in {".", ".."}:
        raise ValueError(f"Unsafe filename: {value!r}")
    return name


def fetch_source(url: str, timeout: int = 60):
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("Only explicit HTTPS source URLs are allowed")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        headers = {
            "content_type": response.headers.get("Content-Type"),
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
        final_url = response.geturl()
    if len(raw) < 50:
        raise ValueError(f"Refusing implausibly small source payload ({len(raw)} bytes)")
    return raw, headers, final_url


def load_manifest(path: pathlib.Path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("methodology_status") != "FROZEN_SPEC":
        raise ValueError("Prospective capture manifest must declare FROZEN_SPEC")
    sources = manifest.get("required_sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Manifest has no required_sources")
    ids = [x.get("id") for x in sources]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("Source ids must be present and unique")
    return manifest


def unresolved_sources(manifest):
    bad = []
    for source in manifest["required_sources"]:
        if source.get("status") != "VALIDATED_FETCH" or not source.get("url"):
            bad.append(source.get("id") or "UNKNOWN")
    return bad


def capture(vintage: str, manifest_path: pathlib.Path, allow_incomplete: bool = False):
    manifest = load_manifest(manifest_path)
    unresolved = unresolved_sources(manifest)
    attempted_at = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    AUDIT_ROOT.mkdir(exist_ok=True)
    audit_path = AUDIT_ROOT / f"prospective-money-capture-{vintage}.json"

    if unresolved and not allow_incomplete:
        audit = {
            "capture": "GMLI prospective Money Core raw-input capture",
            "vintage": vintage,
            "attempted_at": attempted_at,
            "status": "BLOCKED_UNRESOLVED_REQUIRED_SOURCES",
            "core_modified": False,
            "unresolved_required_sources": unresolved,
            "manifest_path": str(manifest_path.relative_to(ROOT)),
            "manifest_sha256": sha256_path(manifest_path),
            "note": "No source bytes were captured. Resolve every required source explicitly; do not substitute guessed or brittle endpoints."
        }
        audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        return audit, 2

    vintage_root = CAPTURE_ROOT / vintage
    raw_root = vintage_root / "raw"
    if vintage_root.exists():
        raise FileExistsError(
            f"Capture directory already exists for {vintage}; refusing to overwrite preserved bytes"
        )
    raw_root.mkdir(parents=True)

    captured = []
    failures = []
    skipped = []
    for source in manifest["required_sources"]:
        sid = source["id"]
        if source.get("status") != "VALIDATED_FETCH" or not source.get("url"):
            skipped.append(sid)
            continue
        try:
            filename = safe_filename(source["filename"])
            raw, headers, final_url = fetch_source(source["url"])
            out = raw_root / filename
            out.write_bytes(raw)
            captured.append({
                "id": sid,
                "region": source.get("region"),
                "role": source.get("role"),
                "source_authority": source.get("source_authority"),
                "series": source.get("series"),
                "requested_url": source["url"],
                "final_url": final_url,
                "filename": str(out.relative_to(vintage_root)),
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
                "response": headers,
            })
        except Exception as exc:
            failures.append({"id": sid, "error": str(exc)[:1000]})

    status = "PASS_RAW_BYTES_PRESERVED" if not failures and not skipped else "INCOMPLETE_CAPTURE"
    lock = {
        "capture": "GMLI prospective Money Core raw-input capture",
        "contract_version": manifest.get("version"),
        "vintage": vintage,
        "captured_at": attempted_at,
        "status": status,
        "methodology_status": "FROZEN_SPEC",
        "core_modified": False,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": sha256_path(manifest_path),
        "capture_runner": str(pathlib.Path(__file__).relative_to(ROOT)),
        "capture_runner_sha256": sha256_path(pathlib.Path(__file__)),
        "frozen_state_sha256": sha256_path(ROOT / "lib" / "state.js"),
        "captured_sources": captured,
        "skipped_sources": skipped,
        "failures": failures,
        "promotion_allowed": False,
        "next_gate": "TRANSFORM_AND_FROZEN_TESTS_NOT_EXECUTED",
        "note": "This lock proves preserved source bytes only. It is not a Core promotion decision."
    }
    lock_path = vintage_root / "manifest.lock.json"
    lock_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    audit_path.write_text(json.dumps(lock, indent=2), encoding="utf-8")
    return lock, 0 if status == "PASS_RAW_BYTES_PRESERVED" else 3


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True, type=validate_vintage)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Research/debug only: capture validated sources while leaving unresolved sources skipped. Never promotion-eligible.",
    )
    args = parser.parse_args()
    manifest_path = pathlib.Path(args.manifest).resolve()
    try:
        result, code = capture(args.vintage, manifest_path, args.allow_incomplete)
        print(json.dumps(result, indent=2))
        raise SystemExit(code)
    except Exception as exc:
        print(json.dumps({
            "status": "CAPTURE_ERROR",
            "core_modified": False,
            "error": str(exc)
        }, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
