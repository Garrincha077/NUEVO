# Bank Impulse → GLD 6M incremental research

Status: **CLOSED / STOP_RESEARCH_DIAGNOSTIC / NOT PROMOTED**

This folder contains the fixed follow-up to the Liquidity Context 24-test screen.

Question: does Bank Balance-Sheet Impulse add stable GLD 6M information beyond the existing GMLI GLD Money predictor (`FX-neutral accel3`)?

Answer: **not robustly enough for promotion**.

The predeclared gate failed because:
- aggregate OOS error improved only slightly (`incremental R² ≈ +0.97%`);
- OOS prediction correlation deteriorated from about `+0.581` for Money-only to `+0.385` with Bank Impulse;
- only `3/6` fixed non-overlapping OOS phases improved.

Positive train/HAC evidence is therefore treated as episodic/regime information rather than stable incremental production value.

Permanent use rule:
- Bank Impulse remains **informational Liquidity Context**;
- scoring effect `NONE`;
- automatic weight `0`;
- no conviction points;
- no CORE/OVERLAY promotion;
- do not optimize this failed relation further without a materially new, explicitly frozen research question.

See:
- `FROZEN_SPEC.md` for the pre-result protocol;
- `RESULT_SUMMARY.md` / `RESULT_SUMMARY.json` for the closeout result;
- GitHub Actions run `33196142937` for the successful reproducible execution.
