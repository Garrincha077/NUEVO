# Citrini Fed → Bank Handoff v1 — result summary

Status: **STOP_RESEARCH_DIAGNOSTIC**

Evidence tier: **RESEARCH_DIAGNOSTIC**  
Scoring effect: **NONE**  
Automatic weight change: **0**  
Methodology effect: **NONE**

Successful frozen Actions run: `33198182785`.

## Question tested

Does the Citrini-style `PRIVATE_HANDOFF` state — **Fed 13W balance-sheet change < 0 while commercial-bank 13W balance-sheet change > 0** — add stable forward information beyond the six already-promoted GMLI Money transmission baselines?

The state/window/sign, one-month lag, six asset/horizon relations, train/OOS split and family gate were frozen before any successful result. The original FRED `WALCL` transport timed out before producing results; before the successful run it was replaced only at the transport layer with the Federal Reserve H.4.1 DDP `RESPPA_N.WW` official total-assets series. `SOURCE_PATH_ADDENDUM.md` records that substitution. No empirical rule changed.

## Fixed family gate

- Positive train PRIVATE_HANDOFF beta: **4/6** — PASS
- Positive OOS incremental R²: **3/6** — FAIL (required ≥4/6)
- Median OOS incremental R²: **+0.0050** — PASS
- Candidate OOS prediction correlation not worse: **0/6** — FAIL (required ≥4/6)
- Fixed non-overlap phase wins: **25/60** — FAIL (required >50%)
- Median non-overlap phase incremental R²: **-0.0259** — FAIL

Because every frozen gate check had to pass, the classification is mechanically **`STOP_RESEARCH_DIAGNOSTIC`**.

## Fixed relation results

| Relation | Train β handoff | HAC p | OOS incr R² | Corr baseline → candidate | Phase wins | OOS handoff − other return |
|---|---:|---:|---:|---:|---:|---:|
| SPY_USD_ACCEL3_12M | +0.0054 | 0.9110 | +0.0197 | +0.3654 → +0.3629 | 7/12 | -0.0001 |
| QQQ_USD_ACCEL3_12M | +0.0778 | 0.3023 | +0.0524 | +0.5682 → +0.5261 | 5/12 | +0.0182 |
| GLD_FXN_ACCEL3_12M | +0.0424 | 0.3658 | +0.0858 | +0.6024 → +0.3811 | 9/12 | +0.0680 |
| DBC_USD_LEVEL_6M | -0.0156 | 0.5664 | -0.0511 | +0.5941 → +0.5879 | 1/6 | +0.0338 |
| DBC_USD_LEVEL_12M | -0.1189 | 0.0040 | -0.5403 | +0.5726 → +0.0679 | 0/12 | +0.1258 |
| DBC_FXN_LEVEL_6M | +0.0243 | 0.4447 | -0.0098 | +0.6856 → +0.6783 | 3/6 | +0.0338 |

## State coverage

Across the aligned Fed/H.8 history there are 282 monthly states:
- `BROAD_EASING`: 143
- `PRIVATE_HANDOFF`: 96
- `TRUE_TIGHTENING`: 25
- `FED_OFFSET`: 18

Train 2015–2022 contains 41 PRIVATE_HANDOFF months; OOS 2023+ contains 25. The failure is therefore not simply absence of the candidate regime in the evaluation sample.

## Interpretation

The Citrini narrative has some **descriptive and episodic asset information**, but it does not pass a broad incremental forecasting test once the already-promoted Money signal is controlled for.

The strongest apparent OOS case is GLD 12M: incremental R² **+0.0858** and 9/12 non-overlap phases improve. However its candidate prediction correlation falls materially from **+0.6024 to +0.3811**, and the train PRIVATE_HANDOFF coefficient is not HAC-significant (`p=0.3658`). QQQ also gains some OOS SSE but loses prediction correlation and fails phase robustness.

DBC is the clearest counterexample. Both promoted 6M relations have negative OOS incremental R², while DBC USD 12M deteriorates severely (`-0.5403`) and its train handoff coefficient is significantly **negative** (`p=0.0040`). This prevents interpreting PRIVATE_HANDOFF as a universal liquidity-supportive state across GMLI assets.

## Decision

**STOP. Do not promote or optimize the Fed→Bank Handoff relation further under this construction.**

It may remain useful as a **descriptive Liquidity Context / current macro narrative label**, but:
- no GMLI score effect;
- no conviction points;
- no automatic allocation weight;
- no CORE or OVERLAY promotion;
- no rescue search over windows, thresholds, lags, states, assets or subperiods.

Under the previously agreed Pareto workflow, this failed family gate also means **do not proceed automatically to a Bank Releveraging composite as a new predictive layer**. A future bank-asset-mix study would need a materially new, explicitly frozen research question rather than serving as a rescue of this failed Citrini handoff hypothesis.
