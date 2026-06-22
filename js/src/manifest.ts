/**
 * CCX manifest schema validation and typed parse.
 *
 * Port-of-record: `src/ccx/manifest.py` + `src/ccx/schemas/manifest.schema.json`
 * (JSON-Schema draft 2020-12). The validating loader mirrors the Python
 * `validate_manifest_data` / `load_manifest` pair: validate against the bundled
 * schema, then map the snake_case JSON onto the camelCase `CcxManifest`.
 */

import Ajv2020 from "ajv/dist/2020";

import schema from "./schema/manifest.schema.json";
import { CcxValidationError } from "./errors";
import type { CcxManifest, GraphEntry, AssetEntry } from "./types";

const ajv = new Ajv2020({ allErrors: false, strict: false });
const validate = ajv.compile(schema);

/**
 * Throw `CcxValidationError` if *data* does not satisfy the manifest schema.
 *
 * The message mirrors the Python reader:
 * `manifest.json failed schema validation at <instancePath>: <message>`.
 */
export function validateManifestData(data: unknown): void {
  if (!validate(data)) {
    const e = validate.errors?.[0];
    throw new CcxValidationError(
      `manifest.json failed schema validation at ${e?.instancePath || "/"}: ${e?.message}`,
    );
  }
}

/** Validate *data* and build a `CcxManifest`, mapping snake_case -> camelCase. */
export function loadManifest(data: any): CcxManifest {
  validateManifestData(data);

  const graphs: GraphEntry[] = (data.graphs as any[]).map((g) => ({
    namespace: g.namespace,
    name: g.name,
    role: g.role ?? null,
    path: g.path,
    mediaType: g.media_type,
    sha256: g.sha256,
    sha512: g.sha512,
    license: g.license ?? null,
  }));

  const assets: AssetEntry[] = ((data.assets as any[]) ?? []).map((a) => ({
    path: a.path,
    mediaType: a.media_type,
    sha256: a.sha256,
    sha512: a.sha512,
    sourceMode: a.source_mode ?? null,
    license: a.license ?? null,
  }));

  return {
    ccxVersion: data.ccx_version,
    name: data.name,
    packageVersion: data.package_version,
    license: data.license ?? null,
    baseIri: data.base_iri ?? null,
    generator: data.generator ?? null,
    graphs,
    assets,
    raw: data,
  };
}
