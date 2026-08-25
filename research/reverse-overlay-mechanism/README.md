# GMLI reverse overlay mechanism research

Status: **RESEARCH ONLY — NO PRODUCTION CHANGE**

Recorded: 2026-08-25

## Question
Repeated Fiscal/Funding diagnostics suggested that the reverse direction may be stronger than the intuitive story that the overlays lead equities. This study asks whether equities statistically precede changes in Fiscal V2 / Funding V2 and whether that result survives fixed robustness checks.

## Main finding

### Funding V2
The reverse pattern is real enough to keep as a permanent research finding, but its interpretation is narrower than “stocks cause Funding.”

- Full sample: all 6 fixed SPY/QQQ -> Funding Granger tests at 1/3/6M survive Holm correction; 0/6 Funding -> equities tests survive.
- Excluding 2020-03..2021-12: again 6/6 market -> Funding and 0/6 Funding -> market.
- Post-2022 fixed 3M follow-up: SPY -> Funding Holm p=0.0175; QQQ -> Funding Holm p=0.0186; reverse direction is not significant.
- Raw-input attribution: market precedence is strongest for ANFCI and reserves, with some term-premium evidence; real-yield evidence is borderline after Holm.
- Nested controls: SPY lags are strongly incremental with Funding own lags only (p=0.0011) and remain so after UNRATE (p=0.0011), but become non-significant after adding VIX (p=0.0614; VIX+UNRATE p=0.0525).

Interpretation: much of the equity -> Funding relationship is a shared **financial-stress / volatility channel**. That makes Funding more naturally a confirmation/conditions overlay than a standalone equity-leading signal.

The result is also regime-dependent: the fixed 3M subperiod test is weak in 2006-2012 and 2013-2019 but strong in 2020+.

The earlier inverted-Funding equity observation is therefore best understood as recent-regime contrarian/rebound context, not a universal production rule.

### DBC
The promoted Funding usefulness gate remains a long-horizon association:
- DBC -> Funding: no Holm-significant Granger result at 1/3/6M.
- Funding -> DBC: no Holm-significant Granger result at 1/3/6M.
- The same holds after excluding the pandemic interval.

This does **not** invalidate the predeclared positive DBC 6M/12M usefulness gate; it means the evidence should not be upgraded into a short-horizon causal-transmission claim.

### Fiscal V2
Fiscal reverse evidence is materially weaker:
- Full sample: only SPY -> Fiscal at 3M survives Holm (p=0.0356).
- No Fiscal -> SPY/QQQ test survives.
- Excluding 2020-03..2021-12 removes the corrected market -> Fiscal significance.
- With VIX and UNRATE controls, joint SPY lags are not significant (p=0.7709).
- Trailing 12M equity association is stronger than forward 12M association.

Interpretation: Fiscal looks **mixed / regime-dependent / policy-reactive**, not a robust leading equity signal.

## Production boundary
No production implication follows automatically. Money Core, Funding V2, Fiscal V2, the 10-point conviction rubric, thresholds and automatic weights are unchanged. Any production use of reverse behavior requires a separately versioned methodology candidate and frozen decision gate.

## Reproducibility
Frozen specs:
- `RESEARCH_SPEC.json`
- `FOLLOWUP_SPEC.json`

Runners:
- `scripts/test-reverse-overlay-mechanism.py`
- `scripts/run-reverse-overlay-mechanism.py`
- `scripts/test-reverse-overlay-followup.py`

Recorded summary:
- `RESULT_SUMMARY.json`

Latest successful audit run: `32831205376`
Artifact: `9556808081`
SHA256: `b4fa10da912d30ef3a8b6995bfad11051ccf3f67d1d53817213f991fd78b4247`
