/**
 * Higher-conformance-class detection over an opened package.
 *
 * Port-of-record: `src/ccx/conformance.py`. Core is validated in `package.ts`.
 * Each checker takes an opened `CcxPackage` and returns `{ present, issues }`:
 *
 * - `present` — the class's artifacts are in the package (so the package is
 *   *claiming* the class).
 * - `issues` — empty when the package conforms to the class; otherwise a list of
 *   human-readable problems.
 *
 * A class is granted (added to `ValidationReport.classes`) only when it is present
 * and has no issues. A present-but-malformed extension does **not** fail Core
 * validation — it surfaces warnings and is simply not granted the class. Absence
 * is never an error.
 */

import { SHAPES_PATH, SOURCE_MODES, SOURCES_PATH } from "./constants";
import type { CcxPackage } from "./package";

/** The result of a single conformance-class checker. */
export interface CheckerResult {
  present: boolean;
  issues: string[];
}

/** A conformance-class checker: probe an opened package for one extension class. */
export type Checker = (pkg: CcxPackage) => Promise<CheckerResult>;

/**
 * Core + Sources: `sources.jsonl` is valid JSON Lines, media modes are valid, and
 * offset selectors stay within their referenced text asset.
 */
export async function checkSources(pkg: CcxPackage): Promise<CheckerResult> {
  if (!pkg.container.has(SOURCES_PATH)) {
    return { present: false, issues: [] };
  }
  const issues: string[] = [];

  const raw = await pkg.container.readText(SOURCES_PATH);
  const records: Record<string, unknown>[] = [];
  const lines = raw.split(/\r\n|\r|\n/);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim()) continue;
    try {
      records.push(JSON.parse(line) as Record<string, unknown>);
    } catch (exc) {
      issues.push(`sources.jsonl line ${i + 1} is not valid JSON: ${(exc as Error).message}`);
    }
  }

  const rawAssets = (pkg.manifest.raw.assets as Record<string, unknown>[] | undefined) ?? [];
  for (const asset of rawAssets) {
    const mode = asset.source_mode;
    if (mode != null && !(SOURCE_MODES as readonly string[]).includes(mode as string)) {
      issues.push(
        `asset ${JSON.stringify(asset.path)} has invalid source_mode ${JSON.stringify(mode)} ` +
          `(expected one of ${SOURCE_MODES.join(", ")})`,
      );
    }
  }

  const textLen: Record<string, number> = {};
  for (const rec of records) {
    const selector = rec.selector;
    if (typeof selector !== "object" || selector === null || Array.isArray(selector)) {
      continue;
    }
    const sel = selector as Record<string, unknown>;
    const start = sel.start;
    const end = sel.end;
    if (start == null && end == null) {
      continue; // a non-offset selector (e.g. a Media Fragment) — not range-checked
    }
    if (
      !Number.isInteger(start) ||
      !Number.isInteger(end) ||
      (start as number) < 0 ||
      (end as number) < (start as number)
    ) {
      issues.push(`record ${JSON.stringify(rec["@id"])}: invalid offset selector (start/end)`);
      continue;
    }
    const textRef = rec.text;
    if (typeof textRef === "string" && pkg.container.has(textRef)) {
      if (!(textRef in textLen)) {
        textLen[textRef] = (await pkg.container.readText(textRef)).length;
      }
      if ((end as number) > textLen[textRef]) {
        issues.push(
          `record ${JSON.stringify(rec["@id"])}: selector end ${end} exceeds ` +
            `text length ${textLen[textRef]} for ${JSON.stringify(textRef)}`,
        );
      }
    }
  }

  return { present: true, issues };
}

/**
 * Shapes: `shapes.ttl` is present, looks like Turtle, and declares at least one
 * SHACL NodeShape or PropertyShape.
 *
 * The Python reader uses rdflib to confirm ≥1 `sh:NodeShape`/`sh:PropertyShape`.
 * To avoid an rdflib-scale dependency, this is an intentionally **lighter,
 * token-presence check**: a non-empty, plausibly-well-formed Turtle body (has a
 * statement terminator `.` or a prefix declaration) that mentions `sh:NodeShape`
 * or `sh:PropertyShape` (CURIE form) or the full SHACL IRI. `shapes-minimal.ccx`
 * must pass and a non-shape Turtle must fail. (Full SHACL parsing is out of scope
 * for the reader; a verifier needing it can layer an optional dep on top.)
 */
export async function checkShapes(pkg: CcxPackage): Promise<CheckerResult> {
  if (!pkg.container.has(SHAPES_PATH)) {
    return { present: false, issues: [] };
  }
  const text = await pkg.container.readText(SHAPES_PATH);

  // Basic well-formedness sniff: non-empty and looks like Turtle (a statement
  // terminator or a prefix/base declaration). A blob of arbitrary text is not.
  const trimmed = text.trim();
  if (!trimmed || !(/\./.test(text) || /@prefix|@base|PREFIX|BASE/i.test(text))) {
    return { present: true, issues: ["shapes.ttl is not valid Turtle: empty or not Turtle-shaped"] };
  }

  const SHACL = "http://www.w3.org/ns/shacl#";
  const hasShape =
    /(^|\W)sh:NodeShape(\W|$)/.test(text) ||
    /(^|\W)sh:PropertyShape(\W|$)/.test(text) ||
    text.includes(`${SHACL}NodeShape`) ||
    text.includes(`${SHACL}PropertyShape`);

  if (!hasShape) {
    return { present: true, issues: ["shapes.ttl declares no SHACL NodeShape or PropertyShape"] };
  }
  return { present: true, issues: [] };
}

/**
 * Embeddings: each manifest embedding descriptor is well-formed, and every
 * `included` descriptor points at a declared, present sidecar asset.
 *
 * (The descriptor's required `model`/`dimensions` and `dimensions >= 1` are
 * enforced structurally by the manifest JSON Schema at Core; this checker adds the
 * semantic rule that an included sidecar must actually be in the package.)
 */
export async function checkEmbeddings(pkg: CcxPackage): Promise<CheckerResult> {
  const descriptors = pkg.manifest.raw.embeddings as unknown[] | undefined;
  if (!descriptors || descriptors.length === 0) {
    return { present: false, issues: [] };
  }
  const issues: string[] = [];
  const assetPaths = new Set(pkg.manifest.assets.map((a) => a.path));
  for (let i = 0; i < descriptors.length; i++) {
    const descriptor = descriptors[i];
    if (typeof descriptor !== "object" || descriptor === null || Array.isArray(descriptor)) {
      issues.push(`embeddings[${i}] is not an object`);
      continue;
    }
    const d = descriptor as Record<string, unknown>;
    if (d.included) {
      const path = d.path;
      if (!path) {
        issues.push(`embeddings[${i}] is included but declares no sidecar path`);
      } else if (!assetPaths.has(path as string) || !pkg.container.has(path as string)) {
        issues.push(
          `embeddings[${i}] sidecar is not a declared, present asset: ${JSON.stringify(path)}`,
        );
      }
    }
  }
  return { present: true, issues };
}

/**
 * Signed: at least one declared signature verifies over the manifest bytes
 * (offline, fail-closed). The class is granted only when a signature actually
 * verifies; signatures that are present but unverifiable leave the class ungranted
 * with a warning.
 */
export async function checkSigned(pkg: CcxPackage): Promise<CheckerResult> {
  const signatures = pkg.manifest.raw.signatures as unknown[] | undefined;
  if (!signatures || signatures.length === 0) {
    return { present: false, issues: [] };
  }
  const results = await pkg.verifySignatures();
  if (results.some((r) => r.verified)) {
    return { present: true, issues: [] };
  }
  const reasons = results.map((r) => r.error || "did not verify").join("; ");
  return { present: true, issues: [`no signature verified: ${reasons}`] };
}

/**
 * Ordered list of [class-name, checker]. `validate()` consults this after Core
 * passes. Higher classes are independent capabilities over Core, not a stack.
 */
export const CHECKERS: ReadonlyArray<readonly [string, Checker]> = [
  ["sources", checkSources],
  ["shapes", checkShapes],
  ["embeddings", checkEmbeddings],
  ["signed", checkSigned],
];
