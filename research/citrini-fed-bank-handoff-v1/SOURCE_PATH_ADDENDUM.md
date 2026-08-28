# Fed source-path addendum — frozen before any successful result

Status: **TECHNICAL SOURCE SUBSTITUTION ONLY / NO METHODOLOGY CHANGE**

The original frozen specification named FRED `WALCL` as the Fed total-assets transport path. GitHub Actions run `33197919134` failed before producing any research result because the FRED CSV read timed out repeatedly.

Before any successful empirical run, the transport path is therefore replaced with the Federal Reserve Board's own H.4.1 Data Download Program series:

- release: `H41`
- series: `RESPPA_N.WW`
- description: `Assets: Total Assets: Total assets: Wednesday level`
- history starts 2002-12-18, matching the total-assets concept used by FRED `WALCL`.

Only the fetch path changes. The frozen construction remains exactly the same:
- latest weekly observation in each month;
- 13-week percentage change versus approximately 91 days earlier;
- one-month conservative availability lag;
- `PRIVATE_HANDOFF = Fed 13W < 0 AND Bank 13W > 0`;
- same six promoted Money relations, same horizons, same train/OOS split and same family gate.

No market result was observed before this substitution. No parameter, sign, horizon, asset, threshold or state rule is changed.
