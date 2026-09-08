/**
 * Simple offline metrics for comparing actual vs expected strings.
 */

/** Exact string equality (trimmed). */
export function exactMatch(actual, expected) {
  const a = String(actual ?? "").trim();
  const e = String(expected ?? "").trim();
  return {
    name: "exact_match",
    pass: a === e,
    score: a === e ? 1 : 0,
  };
}

/** Case-insensitive equality (trimmed). */
export function caseInsensitiveMatch(actual, expected) {
  const a = String(actual ?? "").trim().toLowerCase();
  const e = String(expected ?? "").trim().toLowerCase();
  return {
    name: "case_insensitive_match",
    pass: a === e,
    score: a === e ? 1 : 0,
  };
}

/** Whether expected is a substring of actual (trimmed, case-sensitive). */
export function contains(actual, expected) {
  const a = String(actual ?? "");
  const e = String(expected ?? "").trim();
  const pass = e.length === 0 ? a.length === 0 : a.includes(e);
  return {
    name: "contains",
    pass,
    score: pass ? 1 : 0,
  };
}

/**
 * Token Jaccard similarity over whitespace-split tokens (lowercased).
 * score in [0, 1]; pass when score >= threshold (default 0.8).
 */
export function tokenOverlap(actual, expected, threshold = 0.8) {
  const tokenize = (s) =>
    String(s ?? "")
      .toLowerCase()
      .trim()
      .split(/\s+/)
      .filter(Boolean);

  const aToks = new Set(tokenize(actual));
  const eToks = new Set(tokenize(expected));

  if (aToks.size === 0 && eToks.size === 0) {
    return { name: "token_overlap", pass: true, score: 1, threshold };
  }
  if (aToks.size === 0 || eToks.size === 0) {
    return { name: "token_overlap", pass: false, score: 0, threshold };
  }

  let inter = 0;
  for (const t of aToks) {
    if (eToks.has(t)) inter += 1;
  }
  const union = aToks.size + eToks.size - inter;
  const score = union === 0 ? 0 : inter / union;
  return {
    name: "token_overlap",
    pass: score >= threshold,
    score: Number(score.toFixed(4)),
    threshold,
  };
}

const REGISTRY = {
  exact_match: exactMatch,
  case_insensitive_match: caseInsensitiveMatch,
  contains,
  token_overlap: tokenOverlap,
};

/**
 * Run named metrics against actual/expected.
 * @param {string} actual
 * @param {string} expected
 * @param {string[]} [metricNames]
 */
export function score(actual, expected, metricNames = ["exact_match"]) {
  const results = [];
  for (const name of metricNames) {
    const fn = REGISTRY[name];
    if (!fn) {
      results.push({
        name,
        pass: false,
        score: 0,
        error: `unknown metric: ${name}`,
      });
      continue;
    }
    results.push(fn(actual, expected));
  }
  return results;
}

export function listMetrics() {
  return Object.keys(REGISTRY);
}
