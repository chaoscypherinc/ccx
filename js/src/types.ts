/**
 * Core public types for the CCX reader.
 *
 * Manifest field names mirror the synced `manifest.schema.json` (snake_case in
 * JSON), but the parsed `CcxManifest` exposes camelCase accessors.
 */

/** A conformance class granted to a package by `validate()`. */
export type CcxClass = "core" | "sources" | "embeddings" | "shapes" | "signed";

/** The result of validating a package. */
export interface ValidationReport {
  ok: boolean;
  errors: string[];
  warnings: string[];
  conformanceLevel: string | null;
  classes: CcxClass[];
}

/** A parsed JSON-LD graph document loaded from the package. */
export interface GraphDocument {
  namespace: string;
  name: string;
  role: string | null;
  path: string;
  doc: unknown;
}

/** A graph entry as declared in `manifest.graphs[]`. */
export interface GraphEntry {
  namespace: string;
  name: string;
  role?: string | null;
  path: string;
  mediaType: string;
  sha256: string;
  sha512: string;
  license?: string | null;
}

/** An asset entry as declared in `manifest.assets[]`. */
export interface AssetEntry {
  path: string;
  mediaType: string;
  sha256: string;
  sha512: string;
  sourceMode?: string | null;
  license?: string | null;
}

/** A parsed CCX manifest. `raw` is the original snake_case JSON object. */
export interface CcxManifest {
  ccxVersion: string;
  name: string;
  packageVersion: string;
  license: string | null;
  baseIri: string | null;
  generator: string | null;
  graphs: GraphEntry[];
  assets: AssetEntry[];
  raw: Record<string, unknown>;
}

/** The outcome of verifying a single signature entry. */
export interface SignatureResult {
  path: string;
  format: string;
  verified: boolean;
  error?: string;
  publicKey?: string;
}

/** Generic, vendor-neutral statistics computed from the default graph. */
export interface PackageStats {
  nodeCount: number;
  edgeCount: number;
  sourceCount: number;
}
