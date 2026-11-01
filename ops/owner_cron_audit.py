"""Read-only cross-repository cron execution audit; publication is NOT verified.

Supplementary GitHub-side signal. The external morning ChatGPT watchdog handles
publication/session/Telegram verification and authorized recovery.
No POST/PATCH requests, retries, dispatches, scores or alerts are implemented.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime, time as clock_time, timedelta
from pathlib import Path
from typing import Any
from urllib import error, parse, request
from zoneinfo import ZoneInfo

import yaml

ZONE = ZoneInfo("Europe/Zagreb")
API = "https://api.github.com"
ALIASES = {
    "month": {name: index for index, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)},
    "dow": {name: index for index, name in enumerate(
        ("sun", "mon", "tue", "wed", "thu", "fri", "sat"))},
}


class AuditIncomplete(Exception):
    """Missing API evidence, unsupported YAML or excessive pagination."""


def _number(value: str, names: dict[str, int] | None) -> int:
    lower = value.lower()
    if names and lower[:3] in names and len(lower) == 3:
        return names[lower]
    if not lower.isdecimal():
        raise ValueError(f"unsupported cron field value: {value!r}")
    return int(lower)


def _field(spec: str, low: int, high: int, names: dict[str, int] | None = None,
           sunday_7: bool = False) -> frozenset[int]:
    selected: set[int] = set()
    for segment in spec.split(","):
        parts = segment.strip().split("/")
        if len(parts) > 2 or not parts[0]:
            raise ValueError(f"invalid cron segment {segment!r}")
        step = int(parts[1]) if len(parts) == 2 and parts[1].isdecimal() else 1
        if step < 1 or (len(parts) == 2 and not parts[1].isdecimal()):
            raise ValueError("invalid cron step")
        interval = parts[0]
        maximum = 7 if sunday_7 else high
        if interval == "*":
            first, last = low, maximum
        elif "-" in interval:
            bounds = interval.split("-")
            if len(bounds) != 2:
                raise ValueError("invalid cron range")
            first, last = (_number(bound, names) for bound in bounds)
        else:
            first = _number(interval, names)
            last = maximum if len(parts) == 2 else first
        if not low <= first <= last <= maximum:
            raise ValueError("cron field outside range")
        selected.update(0 if sunday_7 and x == 7 else x for x in range(first, last + 1, step))
    return frozenset(selected)


class Cron:
    def __init__(self, expression: str):
        fields = expression.strip().split()
        if len(fields) != 5:
            raise ValueError("GitHub cron must have five UTC fields")
        self.expression = expression
        self.minute = _field(fields[0], 0, 59)
        self.hour = _field(fields[1], 0, 23)
        self.day = _field(fields[2], 1, 31)
        self.month = _field(fields[3], 1, 12, ALIASES["month"])
        self.weekday = _field(fields[4], 0, 6, ALIASES["dow"], sunday_7=True)
        self.day_limited = fields[2] != "*"
        self.weekday_limited = fields[4] != "*"

    def matches(self, instant: datetime) -> bool:
        dt = instant.astimezone(UTC)
        weekday = (dt.weekday() + 1) % 7
        day_ok, weekday_ok = dt.day in self.day, weekday in self.weekday
        date_ok = day_ok or weekday_ok if self.day_limited and self.weekday_limited else (
            day_ok and weekday_ok
        )
        return (dt.minute in self.minute and dt.hour in self.hour
                and dt.month in self.month and date_ok)


def previous_morning(now: datetime) -> datetime:
    """Previous calendar day's 10:00 Zagreb, including 23/25-hour DST days."""
    if now.tzinfo is None:
        raise ValueError("now needs timezone")
    yesterday = now.astimezone(ZONE).date() - timedelta(days=1)
    return datetime.combine(yesterday, clock_time(10), tzinfo=ZONE).astimezone(UTC)


def expected_occurrences(crons: list[str], start: datetime, end: datetime) -> list[datetime]:
    if end.tzinfo is None or start.tzinfo is None:
        raise ValueError("range must be timezone-aware")
    if end - start > timedelta(days=3):
        raise ValueError("audit window exceeds three days")
    expressions = [Cron(s) for s in crons]
    cursor = start.astimezone(UTC).replace(second=0, microsecond=0)
    if cursor < start.astimezone(UTC):
        cursor += timedelta(minutes=1)
    found: set[datetime] = set()
    while cursor <= end.astimezone(UTC):
        if any(expression.matches(cursor) for expression in expressions):
            found.add(cursor)
        cursor += timedelta(minutes=1)
    return sorted(found)


def extract_crons(source: str) -> list[str]:
    try:
        loaded = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise AuditIncomplete("malformed workflow YAML") from exc
    if not isinstance(loaded, dict):
        raise AuditIncomplete("workflow YAML is not a mapping")
    events = loaded.get("on", loaded.get(True))  # YAML 1.1 parses on as True.
    if not isinstance(events, dict) or "schedule" not in events:
        return []
    schedules = events["schedule"]
    if not isinstance(schedules, list):
        raise AuditIncomplete("unsupported schedule YAML structure")
    crons = []
    for entry in schedules:
        if not isinstance(entry, dict) or not isinstance(entry.get("cron"), str):
            raise AuditIncomplete("invalid workflow cron item")
        spec = entry["cron"]
        Cron(spec)
        crons.append(spec)
    return crons


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def classify_due(due: list[datetime], runs: list[dict[str, Any]], now: datetime,
                 grace: timedelta = timedelta(minutes=30)) -> list[dict[str, Any]]:
    """Timestamp grouping; NOT proof of exact github.event.schedule.

    A run after the next cron slot cannot be attributed to the earlier slot
    using REST run timestamps alone. Missing means unverified, not proven absent.
    """
    scheduled = sorted((r for r in runs if r.get("event") == "schedule"),
                       key=lambda r: r.get("created_at", ""))
    assigned: set[int] = set()
    result: list[dict[str, Any]] = []
    for index, occurrence in enumerate(due):
        following = due[index + 1] if index + 1 < len(due) else now + timedelta(minutes=1)
        candidates = [(pos, row) for pos, row in enumerate(scheduled)
                      if pos not in assigned
                      and occurrence - timedelta(minutes=5) <= parse_iso(row["created_at"]) < following]
        match = candidates[0] if candidates else None
        if match is None:
            status = "PENDING_GRACE" if now < occurrence + grace else "MISSED_UNVERIFIED"
            result.append({"expectedUTC": occurrence.isoformat(),
                           "expectedZagreb": occurrence.astimezone(ZONE).isoformat(),
                           "status": status, "outputFresh": "NOT_CHECKED"})
            continue
        assigned.add(match[0])
        row = match[1]
        created = parse_iso(row["created_at"])
        late = created > occurrence + grace
        conclusion = row.get("conclusion")
        if row.get("status") != "completed":
            status = "IN_PROGRESS_DELAYED" if late else "IN_PROGRESS"
        elif conclusion == "success":
            status = "DELAYED_OUTPUT_UNVERIFIED" if late else "RUN_SUCCESS_OUTPUT_UNVERIFIED"
        elif conclusion in ("failure", "cancelled", "timed_out", "skipped", "action_required"):
            status = conclusion.upper()
        else:
            status = "UNVERIFIED_CONCLUSION"
        started = parse_iso(row["run_started_at"]) if row.get("run_started_at") else None
        result.append({"expectedUTC": occurrence.isoformat(),
                       "expectedZagreb": occurrence.astimezone(ZONE).isoformat(),
                       "runId": row.get("id"), "runUrl": row.get("html_url"),
                       "createdAtUTC": created.isoformat(),
                       "runStartedAtUTC": started.isoformat() if started else None,
                       "startDelayMinutes": round((started - occurrence).total_seconds() / 60, 1)
                       if started else None, "status": status,
                       "timingMapping": "INFERRED_FROM_CREATED_AT_ONLY",
                       "outputFresh": "NOT_CHECKED"})
    extra = [r for pos, r in enumerate(scheduled) if pos not in assigned
             and parse_iso(r["created_at"]) >= (due[0] if due else now - timedelta(days=1))]
    if extra:
        result.append({"status": "UNMAPPED_SCHEDULE_RUNS", "runIds": [r.get("id") for r in extra],
                       "outputFresh": "NOT_CHECKED"})
    return result


class GitHubAPI:
    def __init__(self, token: str = ""):
        self.token = token
        self.requests = 0

    def get(self, path: str, params: dict[str, str | int] | None = None) -> Any:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("invalid API path")
        suffix = ("?" + parse.urlencode(params)) if params else ""
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "owner-cron-audit/1.0"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        self.requests += 1
        if self.requests > 3000:
            raise AuditIncomplete("API request budget reached")
        try:
            with request.urlopen(request.Request(API + path + suffix, headers=headers), timeout=20) as resp:
                return json.loads(resp.read(6_000_000))
        except error.HTTPError as exc:
            raise AuditIncomplete(f"GitHub REST HTTP {exc.code} at {path.split('?')[0]}") from exc
        except (TimeoutError, error.URLError, json.JSONDecodeError) as exc:
            raise AuditIncomplete(f"GitHub REST unavailable or invalid at {path}") from exc

    def pages(self, path: str, params: dict[str, str | int] | None = None,
              max_pages: int = 15) -> list[Any]:
        output: list[Any] = []
        for page in range(1, max_pages + 1):
            data = self.get(path, {**(params or {}), "per_page": 100, "page": page})
            if not isinstance(data, list):
                raise AuditIncomplete("unexpected paginated API shape")
            output.extend(data)
            if len(data) < 100:
                return output
        raise AuditIncomplete(f"pagination exceeds {max_pages} pages for {path}")


def discover_repositories(api: GitHubAPI, owner: str) -> tuple[list[dict[str, Any]], str]:
    # This runs from a PUBLIC repository. Never disclose private repo names in
    # public Actions logs, job summaries or downloadable artifacts.
    public = api.pages(f"/users/{parse.quote(owner)}/repos", {"type": "owner"})
    if not public:
        raise AuditIncomplete("no publicly discoverable repositories")
    if any(repo.get("private") for repo in public):
        raise AuditIncomplete("unexpected private repository in public API listing")
    return public, "PUBLIC_ONLY_INCOMPLETE_PRIVATE_COVERAGE"


def repo_workflows(api: GitHubAPI, repo: dict[str, Any]) -> list[tuple[str, list[str]]]:
    full = repo["full_name"]
    branch = repo["default_branch"]
    try:
        files = api.get(f"/repos/{full}/contents/.github/workflows", {"ref": branch})
    except AuditIncomplete as exc:
        if "HTTP 404" in str(exc):
            return []
        raise
    if not isinstance(files, list):
        raise AuditIncomplete(f"invalid workflow listing {full}")
    result = []
    for item in files:
        path = item.get("path", "")
        if item.get("type") != "file" or not path.endswith((".yml", ".yaml")):
            continue
        blob = api.get(f"/repos/{full}/contents/{parse.quote(path, safe='/')}", {"ref": branch})
        if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise AuditIncomplete(f"workflow content unavailable {full}/{path}")
        try:
            source = base64.b64decode(blob["content"], validate=False).decode("utf-8")
            expressions = extract_crons(source)
        except (ValueError, UnicodeError) as exc:
            raise AuditIncomplete(f"invalid workflow cron {full}/{path}") from exc
        if expressions:
            result.append((path, expressions))
    return result


def schedule_runs(api: GitHubAPI, repo: str, workflow_path: str,
                  start: datetime) -> list[dict[str, Any]]:
    workflow_file = parse.quote(workflow_path.rsplit("/", 1)[-1])
    results = []
    since = (start - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for page in range(1, 21):
        data = api.get(f"/repos/{repo}/actions/workflows/{workflow_file}/runs",
                       {"event": "schedule", "created": f">={since}",
                        "per_page": 100, "page": page})
        if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
            raise AuditIncomplete(f"invalid Actions runs for {repo}/{workflow_file}")
        batch = data["workflow_runs"]
        results.extend(batch)
        if len(batch) < 100:
            return results
    raise AuditIncomplete(f"Actions runs exceed pagination limit for {repo}/{workflow_file}")


def audit(owner: str, api: GitHubAPI, now: datetime) -> dict[str, Any]:
    start = previous_morning(now)
    repos, scope = discover_repositories(api, owner)
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    workflows = 0
    for repo in repos:
        if repo.get("archived") or repo.get("disabled"):
            continue
        name = str(repo["full_name"])
        try:
            wf = repo_workflows(api, repo)
            for path, crons in wf:
                if name.casefold() == f"{owner}/NUEVO".casefold() and path == ".github/workflows/owner-cron-audit.yml":
                    continue
                workflows += 1
                due = expected_occurrences(crons, start, now)
                if not due:
                    continue
                runs = schedule_runs(api, name, path, start)
                for item in classify_due(due, runs, now):
                    rows.append({"repository": name, "workflow": path, "cronUTC": crons, **item})
        except AuditIncomplete as exc:
            errors.append({"repository": name, "error": str(exc)})
    counts = Counter(r["status"] for r in rows)
    return {"schemaVersion": "owner-cron-execution-audit-v1", "owner": owner,
            "generatedAtUTC": now.astimezone(UTC).isoformat(),
            "windowStartUTC": start.isoformat(), "coverage": scope,
            "repositoriesDiscovered": len(repos), "scheduledWorkflowsSeen": workflows,
            "status": "INCOMPLETE" if errors or scope != "AUTHENTICATED_OWNER_INVENTORY"
                      else "EXECUTION_ONLY_OUTPUT_UNVERIFIED",
            "counts": dict(sorted(counts.items())), "errors": errors, "occurrences": rows,
            "outputFreshness": "NOT_VERIFIED_BY_THIS_TOOL",
            "recoveryOrNotifications": "NONE_READ_ONLY"}


def summary(report: dict[str, Any]) -> str:
    counts = report["counts"]
    lines = ["## Owner cron execution audit (read-only)", "",
             f"- Coverage: **{report['coverage']}**; status: **{report['status']}**",
             f"- Repositories discovered: **{report['repositoriesDiscovered']}**; scheduled workflows: **{report['scheduledWorkflowsSeen']}**",
             f"- Window (UTC): {report['windowStartUTC']} → {report['generatedAtUTC']}",
             "- **Output freshness, publication identity and delivery ledgers are NOT verified here.**",
             "- No recovery, scoring, alert or Telegram actions are performed.", "",
             "| State | Occurrences |", "|---|---:|"]
    lines.extend(f"| {key} | {value} |" for key, value in sorted(counts.items()))
    bad = [x for x in report["occurrences"] if x["status"] not in
           {"RUN_SUCCESS_OUTPUT_UNVERIFIED", "IN_PROGRESS", "PENDING_GRACE"}]
    if bad:
        lines.extend(["", "### Abnormal or uncertain occurrences", "",
                      "| Repository | Workflow | Due (Zagreb) | State | Run |",
                      "|---|---|---|---|---|"])
        for item in bad[:50]:
            run = f"[#{item['runId']}]({item['runUrl']})" if item.get("runUrl") else "—"
            lines.append(f"| {item['repository']} | {item['workflow']} | {item.get('expectedZagreb', '—')} | {item['status']} | {run} |")
    if report["errors"]:
        lines.extend(["", "### Unverifiable repositories"])
        lines.extend(f"- {item['repository']}: {item['error']}" for item in report["errors"][:25])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="Garrincha077")
    parser.add_argument("--output", default="owner-cron-audit.json")
    parser.add_argument("--now", help="UTC ISO-8601 for reproducible offline checks")
    opts = parser.parse_args()
    now = parse_iso(opts.now) if opts.now else datetime.now(UTC)
    api = GitHubAPI(os.getenv("GH_TOKEN", ""))
    try:
        report = audit(opts.owner, api, now)
    except AuditIncomplete as exc:
        report = {"schemaVersion": "owner-cron-execution-audit-v1", "owner": opts.owner,
                  "generatedAtUTC": now.isoformat(), "windowStartUTC": previous_morning(now).isoformat(),
                  "coverage": "UNKNOWN", "repositoriesDiscovered": 0, "scheduledWorkflowsSeen": 0,
                  "status": "INCOMPLETE", "counts": {},
                  "errors": [{"repository": opts.owner, "error": str(exc)}],
                  "occurrences": [], "outputFreshness": "NOT_VERIFIED_BY_THIS_TOOL",
                  "recoveryOrNotifications": "NONE_READ_ONLY"}
    Path(opts.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = summary(report)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(markdown)
    else:
        print(markdown)
    # Partial public coverage is explicit in the JSON; not a failure if the
    # read-only scan itself completed. Any failed API evidence -> exit nonzero.
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
