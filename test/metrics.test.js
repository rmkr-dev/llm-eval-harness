import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  exactMatch,
  caseInsensitiveMatch,
  contains,
  tokenOverlap,
  score,
  listMetrics,
} from "../src/metrics.js";

describe("exactMatch", () => {
  it("passes on identical trimmed strings", () => {
    const r = exactMatch("  hello  ", "hello");
    assert.equal(r.pass, true);
    assert.equal(r.score, 1);
    assert.equal(r.name, "exact_match");
  });

  it("fails on mismatch", () => {
    const r = exactMatch("hello", "Hello");
    assert.equal(r.pass, false);
    assert.equal(r.score, 0);
  });
});

describe("caseInsensitiveMatch", () => {
  it("ignores case", () => {
    const r = caseInsensitiveMatch("Hello", "hello");
    assert.equal(r.pass, true);
    assert.equal(r.score, 1);
  });
});

describe("contains", () => {
  it("passes when expected is substring", () => {
    const r = contains("alpha beta gamma", "beta");
    assert.equal(r.pass, true);
  });

  it("fails when missing", () => {
    const r = contains("alpha beta", "gamma");
    assert.equal(r.pass, false);
  });
});

describe("tokenOverlap", () => {
  it("scores full overlap as 1", () => {
    const r = tokenOverlap("one two three", "three one two");
    assert.equal(r.score, 1);
    assert.equal(r.pass, true);
  });

  it("fails below threshold", () => {
    const r = tokenOverlap("one two", "three four", 0.8);
    assert.equal(r.pass, false);
    assert.ok(r.score < 0.8);
  });

  it("handles empty vs empty", () => {
    const r = tokenOverlap("", "");
    assert.equal(r.pass, true);
    assert.equal(r.score, 1);
  });
});

describe("score / listMetrics", () => {
  it("lists known metrics", () => {
    const names = listMetrics();
    assert.ok(names.includes("exact_match"));
    assert.ok(names.includes("token_overlap"));
  });

  it("runs multiple metrics", () => {
    const results = score("Hello World", "hello world", [
      "exact_match",
      "case_insensitive_match",
    ]);
    assert.equal(results.length, 2);
    assert.equal(results[0].pass, false);
    assert.equal(results[1].pass, true);
  });

  it("flags unknown metrics", () => {
    const results = score("a", "a", ["not_a_metric"]);
    assert.equal(results[0].pass, false);
    assert.match(results[0].error, /unknown metric/);
  });
});
