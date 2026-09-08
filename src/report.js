/**
 * Aggregate case results into a JSON-serializable report.
 */

/**
 * @param {object} opts
 * @param {Array<object>} opts.cases - per-case results
 * @param {string} [opts.fixturesDir]
 * @param {string} [opts.startedAt]
 * @param {string} [opts.finishedAt]
 */
export function buildReport({
  cases,
  fixturesDir = "fixtures",
  startedAt,
  finishedAt,
} = {}) {
  const total = cases.length;
  const passed = cases.filter((c) => c.pass).length;
  const failed = total - passed;

  const metricTotals = {};
  for (const c of cases) {
    for (const m of c.metrics ?? []) {
      if (!metricTotals[m.name]) {
        metricTotals[m.name] = { sum: 0, count: 0, passes: 0 };
      }
      metricTotals[m.name].sum += Number(m.score) || 0;
      metricTotals[m.name].count += 1;
      if (m.pass) metricTotals[m.name].passes += 1;
    }
  }

  const metricsSummary = {};
  for (const [name, t] of Object.entries(metricTotals)) {
    metricsSummary[name] = {
      mean_score: t.count ? Number((t.sum / t.count).toFixed(4)) : 0,
      pass_rate: t.count ? Number((t.passes / t.count).toFixed(4)) : 0,
      n: t.count,
    };
  }

  return {
    harness: "llm-eval-harness",
    version: "0.1.0",
    fixturesDir,
    startedAt: startedAt ?? null,
    finishedAt: finishedAt ?? null,
    summary: {
      total,
      passed,
      failed,
      pass_rate: total ? Number((passed / total).toFixed(4)) : 0,
    },
    metrics: metricsSummary,
    cases,
  };
}

export function formatSummary(report) {
  const { summary, metrics } = report;
  const lines = [
    `Eval: ${summary.passed}/${summary.total} passed (${(summary.pass_rate * 100).toFixed(1)}%)`,
  ];
  for (const [name, m] of Object.entries(metrics ?? {})) {
    lines.push(
      `  ${name}: mean=${m.mean_score} pass_rate=${(m.pass_rate * 100).toFixed(1)}% (n=${m.n})`,
    );
  }
  return lines.join("\n");
}
