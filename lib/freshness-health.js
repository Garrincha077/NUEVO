import { FROZEN_STATE } from './state.js';
import { OVERLAY_REFRESH_STATUS } from './overlay-refresh-status.js';

const DAY_MS = 24 * 60 * 60 * 1000;

function normalizedDate(value) {
  if (!value) return null;
  const s = String(value).trim();
  let m = s.match(/^(20\d{2})-(0[1-9]|1[0-2])$/);
  if (m) {
    const y = Number(m[1]);
    const mo = Number(m[2]);
    return new Date(Date.UTC(y, mo, 0));
  }
  m = s.match(/^(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/);
  if (m) return new Date(`${s}T00:00:00Z`);
  return null;
}

function ageDays(value, now) {
  const d = normalizedDate(value);
  if (!d || Number.isNaN(d.getTime())) return null;
  return Math.max(0, Math.floor((now.getTime() - d.getTime()) / DAY_MS));
}

export function freshnessLabel(age) {
  if (!Number.isFinite(age)) return 'UNKNOWN';
  if (age <= 35) return 'FRESH';
  if (age <= 60) return 'AGING';
  return 'STALE';
}

function item(key, label, tier, date, now, extra = {}) {
  const age_days = ageDays(date, now);
  return {
    key,
    label,
    evidence_tier: tier,
    available_date: date || null,
    age_days,
    freshness: freshnessLabel(age_days),
    ...extra
  };
}

function overlayMeta(key) {
  const x = OVERLAY_REFRESH_STATUS[key];
  if (!x) return {};
  return {
    last_good_date: x.last_good_date || null,
    automation_status: x.automation_status || 'UNKNOWN',
    refreshable: Boolean(x.refreshable),
    refresh_blocker: x.blocker || null,
    methodology_provenance: x.methodology_provenance || 'UNKNOWN',
    refresh_guardrail: x.guardrail || null
  };
}

function minDate(values) {
  const xs = values.filter(Boolean).map(String).sort();
  return xs.length ? xs[0] : null;
}

export function buildFreshnessHealth(decision, opportunity, generatedAt = new Date()) {
  const now = generatedAt instanceof Date ? generatedAt : new Date(generatedAt);
  const nowcastBlocks = decision?.money_nowcast?.blocks || {};
  const coreAssets = ['SPY', 'QQQ', 'GLD', 'DBC'];
  const marketDates = coreAssets.map(k => opportunity?.assets?.[k]?.price_as_of).filter(Boolean);
  const positioningDates = coreAssets
    .map(k => opportunity?.assets?.[k]?.entry_inputs?.positioning?.as_of)
    .filter(Boolean);
  const candidate = FROZEN_STATE.money.promotion_candidate || null;

  const items = [
    item('money_core', 'Active Money Core', 'CORE', FROZEN_STATE.money.available_date, now, {
      decision_critical: true,
      engine_freshness: FROZEN_STATE.money.freshness,
      version: FROZEN_STATE.money.version
    }),
    ...(candidate ? [item('money_candidate', 'Money promotion candidate', 'RESEARCH', candidate.available_date, now, {
      decision_critical: false,
      promotion_gate: FROZEN_STATE.money.promotion_gate?.status || 'UNKNOWN'
    })] : []),
    item('money_nowcast_us', 'Money nowcast — US', 'RESEARCH', nowcastBlocks.us || null, now),
    item('money_nowcast_euro_area', 'Money nowcast — Euro area', 'RESEARCH', nowcastBlocks.euro_area || null, now),
    item('money_nowcast_japan', 'Money nowcast — Japan', 'RESEARCH', nowcastBlocks.japan || null, now),
    item('money_nowcast_china', 'Money nowcast — China', 'RESEARCH', nowcastBlocks.china || null, now),
    item('funding', 'Funding overlay', 'OVERLAY', FROZEN_STATE.funding.available_date, now, {
      decision_critical: true,
      ...overlayMeta('funding')
    }),
    item('credit', 'Credit overlay', 'OVERLAY', FROZEN_STATE.credit.available_date, now, overlayMeta('credit')),
    item('fiscal', 'Fiscal overlay', 'OVERLAY', FROZEN_STATE.fiscal.available_date, now, overlayMeta('fiscal')),
    item('market_structure', 'Core asset completed-month structure', 'RESEARCH', minDate(marketDates), now, {
      decision_critical: true,
      assets: coreAssets
    }),
    item('cftc_positioning', 'Core asset CFTC positioning', 'RESEARCH', minDate(positioningDates), now, {
      decision_critical: false,
      role: 'ENTRY_QUALITY_ONLY'
    })
  ];

  const core = items.find(x => x.key === 'money_core');
  if (core && FROZEN_STATE.money.freshness === 'STALE') core.freshness = 'STALE';

  const critical = items.filter(x => x.decision_critical && Number.isFinite(x.age_days));
  const oldest = [...critical].sort((a, b) => b.age_days - a.age_days)[0] || null;
  const staleCritical = critical.filter(x => x.freshness === 'STALE');
  const agingCritical = critical.filter(x => x.freshness === 'AGING');

  const status = staleCritical.length
    ? (staleCritical.some(x => x.key === 'money_core') ? 'DEGRADED_CORE_STALE' : 'DEGRADED_STALE_INPUT')
    : agingCritical.length
      ? 'AGING'
      : 'HEALTHY';

  const overlays = items.filter(x => ['funding', 'credit', 'fiscal'].includes(x.key));

  return {
    policy: {
      fresh_max_days: 35,
      aging_max_days: 60,
      stale_min_days: 61,
      note: 'Freshness is evaluated against the active promoted data vintage. It never changes frozen methodology; future Core vintages still require an explicit promotion gate.'
    },
    status,
    generated_at: now.toISOString(),
    oldest_decision_critical_input: oldest ? {
      key: oldest.key,
      label: oldest.label,
      available_date: oldest.available_date,
      age_days: oldest.age_days,
      freshness: oldest.freshness
    } : null,
    counts: {
      fresh: items.filter(x => x.freshness === 'FRESH').length,
      aging: items.filter(x => x.freshness === 'AGING').length,
      stale: items.filter(x => x.freshness === 'STALE').length,
      unknown: items.filter(x => x.freshness === 'UNKNOWN').length
    },
    overlay_refreshability: {
      ready: overlays.filter(x => x.refreshable).map(x => x.key),
      blocked_or_pending: overlays.filter(x => !x.refreshable).map(x => ({
        key: x.key,
        status: x.automation_status,
        last_good_date: x.last_good_date,
        blocker: x.refresh_blocker
      }))
    },
    items
  };
}
