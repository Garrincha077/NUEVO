# Owner cron audit — execution evidence only

A **read-only** supplementary GitHub Actions workflow inventories scheduled
workflows on publicly accessible Garrincha077 repositories and compares due UTC
cron occurrences against recent `event=schedule` run creation timestamps.
It uses `Europe/Zagreb` for the previous 10:00 window and report labels
(including DST transitions). GitHub cron expressions themselves remain UTC.

This is **not** a health verification of output publication. It cannot check
source dates, market sessions, manifests, scoring state, Vercel production,
quality gates or once-only delivery ledgers. A green Actions run is never proof
that published data are fresh. The existing connected ChatGPT Morning Watchdog
continues to audit those full chains and execute only supported, idempotent
recovery paths.

This workflow lives in a PUBLIC repository and deliberately enumerates **only
publicly listed repositories**. It never requests account-wide private tokens,
which would risk exposing private repository names in public Actions summaries
or artifacts. Its coverage is *always* labelled
`PUBLIC_ONLY_INCOMPLETE_PRIVATE_COVERAGE` and `status: INCOMPLETE`.
A completed public-only scan may have a green job result without claiming
exhaustive coverage. Any failed GitHub API evidence exits nonzero.

The GitHub REST workflow runs endpoint does not independently prove which
`github.event.schedule` created a run. Slot matching is conservatively labelled
`INFERRED_FROM_CREATED_AT_ONLY`; runs crossing multiple cron slots may be
ambiguous. A `workflow_dispatch` run is not counted as the original cron run.
The primary ChatGPT watchdog separately verifies recovery by the exact
session/output identity, not by a matching workflow name.

The audit runs once daily as a secondary best-effort signal, can be invoked by
`workflow_dispatch`, writes a JSON artifact and GitHub job summary, and
**never** POSTs to GitHub, modifies repositories, retries workflows or sends
Telegram. It cannot repair GitHub-wide runner/scheduler failures.
