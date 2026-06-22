/**
 * JSON-LD graph helpers for the CCX reader.
 *
 * Mirrors the network-safety and default-graph logic in `src/ccx/graphs.py`:
 * - `rejectRemoteContext` -> `reject_remote_context`
 * - `isDefault`           -> `is_default`
 *
 * The reader MUST NOT fetch remote JSON-LD contexts at read time, so any remote
 * `@context` or JSON-LD 1.1 `@import` reference is rejected up front.
 */

import { CcxSecurityError } from "./errors";

/** True when `value` is a string that looks like a remote (http/https) URL. */
function isRemote(value: unknown): value is string {
  return typeof value === "string" && /^https?:\/\//i.test(value);
}

/** True when `value` is a plain object (and not an array or null). */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Throw `CcxSecurityError` if a JSON-LD doc references a remote context anywhere.
 *
 * Walks the whole structure: a remote `@context` (string or list element) or a
 * remote JSON-LD 1.1 `@import` is rejected whether it sits at the top level,
 * inside `@graph`, or in a node-scoped context nested anywhere.
 */
export function rejectRemoteContext(node: unknown): void {
  if (isRecord(node)) {
    const ctx = node["@context"];
    const candidates = Array.isArray(ctx) ? ctx : [ctx];
    for (const candidate of candidates) {
      if (isRemote(candidate)) {
        throw new CcxSecurityError(
          `remote @context not allowed: ${candidate} (bundle it in the package)`,
        );
      }
    }
    const imported = node["@import"];
    if (isRemote(imported)) {
      throw new CcxSecurityError(
        `remote @import not allowed: ${imported} (bundle it in the package)`,
      );
    }
    for (const value of Object.values(node)) {
      rejectRemoteContext(value);
    }
  } else if (Array.isArray(node)) {
    for (const item of node) {
      rejectRemoteContext(item);
    }
  }
}

/**
 * True when a graph entry maps to the RDF default graph: it is explicitly the
 * `default` role, or it lives in the reserved `ccx` namespace.
 */
export function isDefault(e: { role?: string | null; namespace: string }): boolean {
  return e.role === "default" || e.namespace === "ccx";
}
