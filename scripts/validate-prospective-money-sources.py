#!/usr/bin/env python3
"""Validate documented source URLs for prospective GMLI Money capture.

This validator performs read-only network checks. It never transforms data,
changes lib/state.js, or promotes a Money vintage. A source is considered
usable only when its exact HTTPS URL returns a non-trivial payload containing
its expected provider-native series marker.
"""

import argparse
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "research" / "prospective-money-source-manifest.json"
USER_AGENT = "GMLI-source-validation/1.0"


def load_manifest(path: pathlib.Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.get("required_sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Manifest has no required_sources")
    return data


def fetch(url: str, timeout: int, attempts: int):
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("Source URL must be explicit HTTPS")
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/csv,text/plain,application/json,*/*;q=0.1",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return {
                    "raw": raw,
                    "http_status": getattr(response, "status", None),
                    "content_type": response.headers.get("Content-Type"),
                    "final_url": response.geturl(),
                }
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Fetch failed after {attempts} attempts: {last_error}")


def validate_source(source, timeout: int, attempts: int):
    sid = source.get("id") or "UNKNOWN"
    url = source.get("url")
    validation = source.get("validation") or {}
    min_bytes = int(validation.get("min_bytes", 200))
    markers = validation.get("must_contain") or []
    if not url:
        return {"id": sid, "status": "FAIL", "error": "missing url"}
    if not markers:
        return {"id": sid, "status": "FAIL", "error": "missing validation.must_contain"}

    try:
        fetched = fetch(url, timeout=timeout, attempts=attempts)
        raw = fetched.pop("raw")
        text = raw.decode("utf-8", errors="replace")
        missing = [marker for marker in markers if marker not in text]
        if len(raw) < min_bytes:
            raise ValueError(f"payload too small: {len(raw)} < {min_bytes} bytes")
        if missing:
            raise ValueError(f"expected marker(s) missing: {missing}")
        return {
            "id": sid,
            "status": "PASS",
            "bytes": len(raw),
            "markers": markers,
            **fetched,
        }
    except Exception as exc:
        return {"id": sid, "status": "FAIL", "error": str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--ids", help="Comma-separated source ids; default validates all VALIDATED_FETCH sources")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args()

    manifest_path = pathlib.Path(args.manifest).resolve()
    manifest = load_manifest(manifest_path)
    requested = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None

    selected = []
    for source in manifest["required_sources"]:
        if requested is not None:
            if source.get("id") in requested:
                selected.append(source)
        elif source.get("status") == "VALIDATED_FETCH":
            selected.append(source)

    if requested is not None:
        found = {x.get("id") for x in selected}
        missing = sorted(requested - found)
        if missing:
            print(json.dumps({"status": "FAIL", "missing_ids": missing}, indent=2))
            return 2
    if not selected:
        print(json.dumps({"status": "FAIL", "error": "no sources selected"}, indent=2))
        return 2

    results = [validate_source(x, args.timeout, args.attempts) for x in selected]
    failed = [x for x in results if x["status"] != "PASS"]
    out = {
        "validator": "GMLI prospective Money source URL validation",
        "core_modified": False,
        "selected": [x.get("id") for x in selected],
        "status": "PASS" if not failed else "FAIL",
        "results": results,
    }
    print(json.dumps(out, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
