#!/usr/bin/env node
/**
 * Offline eval runner: load golden fixtures, score actual vs expected, emit JSON.
 *
 * Fixture layout (per case directory under fixtures/):
 *   input.txt | input.json   — prompt / inputs (informational)
 *   expected.txt             — golden expected output
 *   actual.txt               — model/agent output to score (optional; skip if missing unless --require-actual)
 *   meta.json                — optional { "id", "metrics": ["exact_match", ...] }
 *
 * Usage:
 *   node src/run-eval.js [--fixtures dir] [--out report.json] [--require-actual]
 */

import { readdir, readFile, writeFile, stat } from "node:fs/promises";
import { join, resolve } from "node:path";
import { score as scoreMetrics } from "./metrics.js";
import { buildReport, formatSummary } from "./report.js";

async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

async function readText(path) {
  return (await readFile(path, "utf8")).replace(/\r\n/g, "\n");
}

async function loadCase(caseDir, caseName) {
  const expectedPath = join(caseDir, "expected.txt");
  const actualPath = join(caseDir, "actual.txt");
  const metaPath = join(caseDir, "meta.json");

  if (!(await exists(expectedPath))) {
    return null;
  }

  const expected = await readText(expectedPath);
  let actual = null;
  let skipped = false;
  if (await exists(actualPath)) {
    actual = await readText(actualPath);
  } else {
    skipped = true;
  }

  let meta = { id: caseName, metrics: ["exact_match"] };
  if (await exists(metaPath)) {
    const raw = JSON.parse(await readText(metaPath));
    meta = {
      id: raw.id ?? caseName,
      metrics: raw.metrics ?? ["exact_match"],
      ...raw,
    };
  }

  return { caseDir, caseName, expected, actual, skipped, meta };
}

async function discoverCases(fixturesDir) {
  const entries = await readdir(fixturesDir, { withFileTypes: true });
  const cases = [];
  for (const ent of entries) {
    if (!ent.isDirectory()) continue;
    if (ent.name.startsWith(".")) continue;
    const loaded = await loadCase(join(fixturesDir, ent.name), ent.name);
    if (loaded) cases.push(loaded);
  }
  cases.sort((a, b) => a.caseName.localeCompare(b.caseName));
  return cases;
}

function parseArgs(argv) {
  const opts = {
    fixtures: "fixtures",
    out: null,
    requireActual: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--fixtures" && argv[i + 1]) {
      opts.fixtures = argv[++i];
    } else if (a === "--out" && argv[i + 1]) {
      opts.out = argv[++i];
    } else if (a === "--require-actual") {
      opts.requireActual = true;
    } else if (a === "--help" || a === "-h") {
      opts.help = true;
    }
  }
  return opts;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    console.log(`Usage: node src/run-eval.js [--fixtures dir] [--out report.json] [--require-actual]`);
    process.exit(0);
  }

  const fixturesDir = resolve(opts.fixtures);
  const startedAt = new Date().toISOString();

  if (!(await exists(fixturesDir))) {
    console.error(`Fixtures directory not found: ${fixturesDir}`);
    process.exit(2);
  }

  const loaded = await discoverCases(fixturesDir);
  if (loaded.length === 0) {
    console.error(`No fixture cases with expected.txt under ${fixturesDir}`);
    process.exit(2);
  }

  const caseResults = [];
  for (const c of loaded) {
    if (c.skipped) {
      if (opts.requireActual) {
        caseResults.push({
          id: c.meta.id,
          path: c.caseName,
          pass: false,
          skipped: false,
          error: "missing actual.txt",
          metrics: [],
        });
        continue;
      }
      caseResults.push({
        id: c.meta.id,
        path: c.caseName,
        pass: true,
        skipped: true,
        metrics: [],
      });
      continue;
    }

    const metrics = scoreMetrics(c.actual, c.expected, c.meta.metrics);
    const pass = metrics.every((m) => m.pass);
    caseResults.push({
      id: c.meta.id,
      path: c.caseName,
      pass,
      skipped: false,
      metrics,
    });
  }

  const finishedAt = new Date().toISOString();
  const report = buildReport({
    cases: caseResults,
    fixturesDir: opts.fixtures,
    startedAt,
    finishedAt,
  });

  const json = JSON.stringify(report, null, 2);
  if (opts.out) {
    await writeFile(opts.out, json + "\n", "utf8");
    console.error(`Wrote ${opts.out}`);
  } else {
    console.log(json);
  }

  console.error(formatSummary(report));

  const failedHard = caseResults.some((c) => !c.pass && !c.skipped);
  process.exit(failedHard ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(2);
});
