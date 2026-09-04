export const MONEY_NOWCAST = {
  "version": "GMLI Current Money Nowcast v1.4 SCHEDULED_VERIFIED",
  "evidence_tier": "RESEARCH",
  "role": "FRESHNESS_OVERLAY_ONLY",
  "methodology_status": "FROZEN_SPEC",
  "comparison_reference": {
    "date": "2026-02-28",
    "label": "LAST_FORMALLY_VALIDATED_CORE_REFERENCE",
    "guardrail": "This reference is used for directional freshness comparison only. Scheduled refresh never changes frozen weights, FX-neutral methodology, lags, horizons, thresholds, train/validation split or FDR rules and never auto-promotes CORE."
  },
  "refresh": {
    "mode": "SCHEDULED_VALIDATED_REFRESH",
    "last_verified_at": "2026-09-04T11:16:53Z",
    "policy": "Update a block only when the official source parser succeeds and sanity checks pass; otherwise preserve the last verified value.",
    "last_result": {
      "us": {
        "status": "PASS",
        "changed": false
      },
      "euro_area": {
        "status": "PASS",
        "changed": false
      },
      "japan": {
        "status": "PASS",
        "changed": false
      },
      "usd_translation": {
        "status": "PASS",
        "changed": false
      },
      "china": {
        "status": "PASS",
        "changed": true,
        "report_month": "2026-07",
        "level_trn_cny": 355.51,
        "yoy_pct": 7.7,
        "source_url": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026081414193264304/index.html",
        "source_article_sha256": "305f395510d16ae2d1ee39c07d71c3e9be3936b550520571d0823e7f97654e00",
        "source_search_sha256": "e7d80e791aac38aef1066ff935f6290b3c59856975ef33e43a18a28c060f24ad"
      }
    }
  },
  "blocks": {
    "us": {
      "name": "United States",
      "aggregate": "M2",
      "latest_date": "2026-07",
      "latest_yoy_pct": 5.4142,
      "core_reference_date": "2026-02",
      "core_reference_yoy_pct": 4.6887,
      "direction_vs_core": "ACCELERATING",
      "delta_vs_core_pp": 0.73,
      "expanding_yoy": true,
      "source": "Federal Reserve / FRED M2SL",
      "source_url": "https://fred.stlouisfed.org/series/M2SL",
      "status": "OK_VERIFIED_SCHEDULED"
    },
    "euro_area": {
      "name": "Euro area",
      "aggregate": "M3",
      "latest_date": "2026-07",
      "latest_yoy_pct": 3.384,
      "core_reference_date": "2026-02",
      "core_reference_yoy_pct": 2.82,
      "direction_vs_core": "ACCELERATING",
      "delta_vs_core_pp": 0.56,
      "expanding_yoy": true,
      "source": "ECB Data Portal BSI",
      "source_url": "https://data.ecb.europa.eu/data/datasets/BSI/BSI.M.U2.Y.V.M30.X.I.U2.2300.Z01.A",
      "status": "OK_VERIFIED_SCHEDULED"
    },
    "japan": {
      "name": "Japan",
      "aggregate": "M2",
      "latest_date": "2026-07",
      "latest_yoy_pct": 2.2,
      "core_reference_date": "2026-02",
      "core_reference_yoy_pct": 1.7,
      "direction_vs_core": "ACCELERATING",
      "delta_vs_core_pp": 0.5,
      "expanding_yoy": true,
      "source": "Bank of Japan Time-Series Data Search API",
      "source_url": "https://www.stat-search.boj.or.jp/api/v1/getDataCode",
      "series_code": "MD02'MAM1YAM2M2MO",
      "status": "OK_VERIFIED_SCHEDULED"
    },
    "china": {
      "name": "China",
      "aggregate": "M2",
      "latest_date": "2026-07",
      "latest_yoy_pct": 7.7,
      "core_reference_date": "2026-02",
      "core_reference_yoy_pct": 9.0,
      "direction_vs_core": "DECELERATING",
      "delta_vs_core_pp": -1.3,
      "expanding_yoy": true,
      "source": "People's Bank of China Financial Statistics Report",
      "status": "OK_VERIFIED_SCHEDULED",
      "note": "Official central PBoC monthly Financial Statistics Report; scheduled parser validates report month, M2 balance and YoY before replacing last-good RESEARCH nowcast data.",
      "source_url": "https://www.pbc.gov.cn/goutongjiaoliu/113456/113469/2026081414193264304/index.html",
      "latest_level_trn_cny": 355.51,
      "source_article_sha256": "305f395510d16ae2d1ee39c07d71c3e9be3936b550520571d0823e7f97654e00",
      "source_search_sha256": "e7d80e791aac38aef1066ff935f6290b3c59856975ef33e43a18a28c060f24ad"
    }
  },
  "usd_translation": {
    "status": "RESEARCH_VERIFIED_SCHEDULED",
    "latest_verified": "2026-08-28",
    "pct_change_since_core": 0.79,
    "translation": "NEUTRAL",
    "source": "Federal Reserve / FRED Broad Dollar Index DTWEXBGS",
    "source_url": "https://fred.stlouisfed.org/series/DTWEXBGS",
    "note": "Translation overlay only; not the frozen FX-neutral Money methodology."
  }
};

export function summarizeNowcast() {
  const blocks = Object.values(MONEY_NOWCAST.blocks);
  const accelerating = blocks.filter(x => x.direction_vs_core === 'ACCELERATING').length;
  const decelerating = blocks.filter(x => x.direction_vs_core === 'DECELERATING').length;
  const stable = blocks.length - accelerating - decelerating;
  const expanding = blocks.filter(x => x.expanding_yoy).length;
  const tilt = accelerating >= 3 && expanding === blocks.length ? 'SUPPORTIVE_MIXED' : accelerating >= decelerating ? 'NEUTRAL_TO_SUPPORTIVE' : 'DETERIORATING';
  return {
    label: accelerating >= 3 ? 'BROADLY_EXPANDING_MIXED_ACCELERATION' : 'MIXED',
    tilt,
    score: null,
    score_status: 'NOT_COMPUTED',
    coverage: `${blocks.length}/${blocks.length}`,
    comparisons_available: `${blocks.length}/${blocks.length}`,
    accelerating,
    stable,
    decelerating,
    expanding_yoy: expanding,
    methodology: 'Unweighted directional freshness overlay versus the last formally validated reference under a frozen specification.'
  };
}
