/**
 * Public surface for `ccx-format` — the TypeScript CCX 3.0 reader/validator.
 *
 * @example
 * ```ts
 * import { readFileSync } from "node:fs";
 * import { openPackage } from "ccx-format";
 *
 * const pkg = await openPackage(readFileSync("knowledge.ccx"));
 * const report = await pkg.validate();
 * if (report.ok) console.log("classes:", report.classes);
 * ```
 */

export { openPackage, CcxPackage } from "./package";

export { CcxError, CcxValidationError, CcxSecurityError, CcxIntegrityError } from "./errors";

export type {
  CcxClass,
  ValidationReport,
  GraphDocument,
  GraphEntry,
  AssetEntry,
  CcxManifest,
  SignatureResult,
  PackageStats,
} from "./types";
