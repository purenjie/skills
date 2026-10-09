#!/usr/bin/env node

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";

const allowedStatuses = new Set([
  "completed",
  "partial",
  "not-tested",
  "not-participated",
  "not-applicable",
  "not-comparable",
  "failed",
  "unknown",
]);

function attrsFrom(raw = "") {
  const attrs = new Map();
  const pattern = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let match;
  while ((match = pattern.exec(raw)) !== null) {
    attrs.set(match[1].toLowerCase(), match[2] ?? match[3] ?? match[4] ?? "");
  }
  return attrs;
}

function stripTags(value = "") {
  return value
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#(?:x20)?39;|&apos;/gi, "'")
    .replace(/&quot;/gi, '"')
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeFragment(value) {
  try {
    return decodeURIComponent(value.replace(/^#/, ""));
  } catch {
    return value.replace(/^#/, "");
  }
}

function validateHtml(html, filePath = "<memory>") {
  const issues = [];
  const add = (level, code, message) => issues.push({ level, code, message });
  const inspected = html
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "");

  if (!/^\s*<!doctype\s+html\b/i.test(html)) {
    add("error", "missing-doctype", "Document must start with an HTML doctype.");
  }
  if (!/<html\b[^>]*>/i.test(inspected) || !/<body\b[^>]*>/i.test(inspected)) {
    add("error", "missing-document-structure", "Document must contain html and body elements.");
  }

  const ids = new Map();
  const elementPattern = /<([a-z][\w:-]*)\b([^>]*)>/gi;
  let match;
  while ((match = elementPattern.exec(inspected)) !== null) {
    const tag = match[1].toLowerCase();
    const attrs = attrsFrom(match[2]);
    const id = attrs.get("id");
    if (id) ids.set(id, (ids.get(id) ?? 0) + 1);

    if (attrs.has("data-report-metric")) {
      if (!attrs.get("data-unit")) {
        add("error", "metric-missing-unit", `${tag}[data-report-metric] is missing data-unit.`);
      }
      if (!attrs.get("data-source")) {
        add("error", "metric-missing-source", `${tag}[data-report-metric] is missing data-source.`);
      }
    }

    if (attrs.has("data-status")) {
      const status = attrs.get("data-status");
      if (!allowedStatuses.has(status)) {
        add("error", "unknown-data-status", `Unsupported data-status value: ${status || "<empty>"}.`);
      } else if (status !== "completed" && !attrs.get("data-reason")) {
        add("error", "status-missing-reason", `${tag}[data-status=${status}] is missing data-reason.`);
      }
    }

    if (attrs.has("data-tooltip")) {
      const focusable = ["a", "button", "input", "select", "textarea"].includes(tag)
        || attrs.has("tabindex");
      if (!focusable) {
        add("error", "tooltip-not-focusable", `${tag}[data-tooltip] must be keyboard-focusable.`);
      }
    }
  }

  for (const [id, count] of ids) {
    if (count > 1) add("error", "duplicate-id", `ID "${id}" appears ${count} times.`);
  }

  const headingPattern = /<h([1-6])\b([^>]*)>([\s\S]*?)<\/h\1>/gi;
  const headings = [];
  while ((match = headingPattern.exec(inspected)) !== null) {
    const level = Number(match[1]);
    const text = stripTags(match[3]);
    headings.push({ level, text });
    if (!text) add("error", "empty-heading", `h${level} heading is empty.`);
  }
  const h1Count = headings.filter((heading) => heading.level === 1).length;
  if (h1Count !== 1) add("error", "h1-count", `Expected exactly one h1, found ${h1Count}.`);
  for (let index = 1; index < headings.length; index += 1) {
    const previous = headings[index - 1];
    const current = headings[index];
    if (current.level > previous.level + 1) {
      add(
        "error",
        "heading-level-jump",
        `Heading level jumps from h${previous.level} "${previous.text}" to h${current.level} "${current.text}".`,
      );
    }
  }

  const anchorPattern = /<a\b([^>]*)>/gi;
  while ((match = anchorPattern.exec(inspected)) !== null) {
    const attrs = attrsFrom(match[1]);
    const href = attrs.get("href");
    if (href === "#" || /^javascript:/i.test(href ?? "")) {
      add("error", "placeholder-link", `Link uses an unusable href: ${href}.`);
    } else if (href?.startsWith("#")) {
      const target = normalizeFragment(href);
      if (!target || !ids.has(target)) {
        add("error", "missing-fragment-target", `Fragment link ${href} has no matching ID.`);
      }
    }
    if (attrs.get("target") === "_blank" && !/\bnoopener\b/i.test(attrs.get("rel") ?? "")) {
      add("warning", "blank-link-without-noopener", `Link ${href || "<without href>"} opens a new tab without rel=noopener.`);
    }
  }

  const ariaRefPattern = /<([a-z][\w:-]*)\b([^>]*)>/gi;
  while ((match = ariaRefPattern.exec(inspected)) !== null) {
    const attrs = attrsFrom(match[2]);
    for (const name of ["aria-describedby", "aria-labelledby"]) {
      const refs = (attrs.get(name) ?? "").split(/\s+/).filter(Boolean);
      for (const ref of refs) {
        if (!ids.has(ref)) add("error", "missing-aria-target", `${name} references missing ID "${ref}".`);
      }
    }
  }

  const imagePattern = /<img\b([^>]*)>/gi;
  while ((match = imagePattern.exec(inspected)) !== null) {
    const attrs = attrsFrom(match[1]);
    if (!attrs.has("alt")) add("error", "image-missing-alt", "Image is missing an alt attribute.");
  }

  const tablePattern = /<table\b([^>]*)>([\s\S]*?)<\/table>/gi;
  while ((match = tablePattern.exec(inspected)) !== null) {
    const attrs = attrsFrom(match[1]);
    const body = match[2];
    if (!/<th\b/i.test(body)) add("error", "table-missing-headers", "Table has no th header cells.");
    if (!/<caption\b/i.test(body) && !attrs.get("aria-label") && !attrs.get("aria-labelledby")) {
      add("warning", "table-missing-label", "Table has no caption, aria-label, or aria-labelledby.");
    }
    if (/<td\b[^>]*>\s*(?:&nbsp;)?\s*<\/td>/i.test(body)) {
      add("warning", "empty-table-cell", "Table contains an empty cell; use an explicit missing-state label when applicable.");
    }
  }

  const infoPattern = /<([a-z][\w:-]*)\b([^>]*)>([^<]*[ⓘℹ][^<]*)<\/\1>/gi;
  while ((match = infoPattern.exec(inspected)) !== null) {
    const tag = match[1].toLowerCase();
    const attrs = attrsFrom(match[2]);
    const accessibleTooltip = attrs.has("data-tooltip") || attrs.has("aria-describedby");
    const focusable = ["a", "button"].includes(tag) || attrs.has("tabindex");
    if (attrs.has("title") && !accessibleTooltip) {
      add("error", "native-title-only", `${tag} info trigger relies only on the native title attribute.`);
    }
    if (!accessibleTooltip || !focusable) {
      add("warning", "inaccessible-info-trigger", `${tag} info trigger should expose its explanation on hover and keyboard focus.`);
    }
  }

  const scriptPattern = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
  while ((match = scriptPattern.exec(html)) !== null) {
    const attrs = attrsFrom(match[1]);
    const src = attrs.get("src");
    const type = attrs.get("type");
    if (src && !/^(?:https?:|data:|\/\/)/i.test(src)) {
      const resolved = path.resolve(path.dirname(filePath), src);
      if (!fs.existsSync(resolved)) add("error", "missing-local-script", `Local script does not exist: ${src}.`);
    } else if (!src && match[2].trim() && type !== "application/json" && type !== "application/ld+json") {
      try {
        new Function(match[2]);
      } catch (error) {
        add("error", "inline-script-syntax", `Inline script does not parse: ${error.message}`);
      }
    }
  }

  return issues;
}

function printIssues(filePath, issues, jsonOutput) {
  if (jsonOutput) {
    process.stdout.write(`${JSON.stringify({ file: filePath, issues }, null, 2)}\n`);
    return;
  }
  if (issues.length === 0) {
    process.stdout.write(`PASS ${filePath}: no deterministic HTML issues found.\n`);
    return;
  }
  for (const issue of issues) {
    process.stdout.write(`${issue.level.toUpperCase()} [${issue.code}] ${issue.message}\n`);
  }
  const errors = issues.filter((issue) => issue.level === "error").length;
  const warnings = issues.length - errors;
  process.stdout.write(`${filePath}: ${errors} error(s), ${warnings} warning(s).\n`);
}

function selfTest() {
  const valid = `<!doctype html><html><body><h1>Report</h1><h2 id="result">Result</h2>
    <a href="#result">Jump</a><span data-report-metric data-unit="ms" data-source="run-1">12</span>
    <span data-status="not-tested" data-reason="out of scope">Not tested</span>
    <button data-tooltip="Definition" aria-describedby="tip">ⓘ</button><span id="tip" role="tooltip">Definition</span>
    <table aria-label="Results"><tr><th>Model</th><th>Time</th></tr><tr><td>A</td><td>12 ms</td></tr></table>
    <img src="chart.png" alt="Execution time comparison"></body></html>`;
  const invalid = `<!doctype html><html><body><h1 id="same">Report</h1><h3 id="same">Skipped</h3>
    <a href="#missing">Broken</a><span title="Only native">ⓘ</span>
    <span data-report-metric>12</span><span data-status="failed">Failed</span>
    <table><tr><td></td></tr></table><img src="x.png"></body></html>`;
  const validErrors = validateHtml(valid).filter((issue) => issue.level === "error");
  const invalidCodes = new Set(validateHtml(invalid).map((issue) => issue.code));
  const expected = [
    "duplicate-id",
    "heading-level-jump",
    "missing-fragment-target",
    "native-title-only",
    "metric-missing-unit",
    "metric-missing-source",
    "status-missing-reason",
    "table-missing-headers",
    "image-missing-alt",
  ];
  const missing = expected.filter((code) => !invalidCodes.has(code));
  if (validErrors.length || missing.length) {
    process.stderr.write(`SELF-TEST FAILED: valid errors=${validErrors.length}, missing checks=${missing.join(", ")}\n`);
    return 1;
  }
  process.stdout.write(`SELF-TEST PASS on ${os.platform()}: valid fixture passes and invalid fixture triggers ${expected.length} expected checks.\n`);
  return 0;
}

const args = process.argv.slice(2);
if (args.includes("--self-test")) {
  process.exitCode = selfTest();
} else {
  const jsonOutput = args.includes("--json");
  const filePath = args.find((arg) => !arg.startsWith("--"));
  if (!filePath) {
    process.stderr.write("Usage: node validate_html_report.mjs <report.html> [--json]\n");
    process.stderr.write("       node validate_html_report.mjs --self-test\n");
    process.exitCode = 2;
  } else {
    const resolved = path.resolve(filePath);
    if (!fs.existsSync(resolved)) {
      process.stderr.write(`File not found: ${resolved}\n`);
      process.exitCode = 2;
    } else {
      const html = fs.readFileSync(resolved, "utf8");
      const issues = validateHtml(html, resolved);
      printIssues(resolved, issues, jsonOutput);
      process.exitCode = issues.some((issue) => issue.level === "error") ? 1 : 0;
    }
  }
}
