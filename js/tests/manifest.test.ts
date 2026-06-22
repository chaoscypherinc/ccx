import { describe, it, expect } from "vitest";

import { validateManifestData, loadManifest } from "../src/manifest";
import { CcxValidationError } from "../src/errors";

/** A minimal schema-valid manifest (snake_case, as it appears in manifest.json). */
function minimalManifest(): Record<string, unknown> {
  return {
    ccx_version: "3.0",
    name: "test-package",
    package_version: "1.0.0",
    graphs: [
      {
        namespace: "https://example.com/ns#",
        name: "knowledge",
        path: "graphs/knowledge.jsonld",
        media_type: "application/ld+json",
        sha256: "a".repeat(64),
        sha512: "b".repeat(128),
      },
    ],
  };
}

describe("validateManifestData", () => {
  it("accepts a minimal valid manifest", () => {
    expect(() => validateManifestData(minimalManifest())).not.toThrow();
  });

  it("throws CcxValidationError when name is missing (mirrors invalid-manifest.ccx)", () => {
    const data = minimalManifest();
    delete data.name;
    expect(() => validateManifestData(data)).toThrow(CcxValidationError);
  });

  it("throws CcxValidationError when graphs is empty (schema minItems 1)", () => {
    const data = minimalManifest();
    data.graphs = [];
    expect(() => validateManifestData(data)).toThrow(CcxValidationError);
  });

  it("produces a message anchored at manifest.json with an instance path", () => {
    const data = minimalManifest();
    delete data.name;
    expect(() => validateManifestData(data)).toThrow(
      /^manifest\.json failed schema validation at/,
    );
  });
});

describe("loadManifest", () => {
  it("maps snake_case to camelCase and exposes typed accessors", () => {
    const m = loadManifest(minimalManifest());
    expect(m.name).toBe("test-package");
    expect(m.packageVersion).toBe("1.0.0");
    expect(m.ccxVersion).toBe("3.0");
    expect(m.graphs).toHaveLength(1);
    expect(m.graphs[0].mediaType).toBe("application/ld+json");
    expect(m.graphs[0].namespace).toBe("https://example.com/ns#");
    expect(m.graphs[0].path).toBe("graphs/knowledge.jsonld");
    expect(m.graphs[0].sha256).toBe("a".repeat(64));
    expect(m.graphs[0].sha512).toBe("b".repeat(128));
    expect(m.assets).toEqual([]);
  });

  it("preserves the original snake_case JSON in raw", () => {
    const data = minimalManifest();
    const m = loadManifest(data);
    expect(m.raw).toBe(data);
    expect((m.raw as Record<string, unknown>).ccx_version).toBe("3.0");
    expect((m.raw as any).graphs[0].media_type).toBe("application/ld+json");
  });

  it("maps assets[] media_type/source_mode to camelCase", () => {
    const data = minimalManifest();
    data.assets = [
      {
        path: "assets/data.csv",
        media_type: "text/csv",
        sha256: "c".repeat(64),
        sha512: "d".repeat(128),
        source_mode: "embedded",
      },
    ];
    const m = loadManifest(data);
    expect(m.assets).toHaveLength(1);
    expect(m.assets[0].mediaType).toBe("text/csv");
    expect(m.assets[0].sourceMode).toBe("embedded");
    expect(m.assets[0].path).toBe("assets/data.csv");
  });

  it("defaults optional manifest fields to null", () => {
    const m = loadManifest(minimalManifest());
    expect(m.license).toBeNull();
    expect(m.baseIri).toBeNull();
    expect(m.generator).toBeNull();
  });

  it("throws CcxValidationError before mapping when invalid", () => {
    const data = minimalManifest();
    delete data.name;
    expect(() => loadManifest(data)).toThrow(CcxValidationError);
  });
});
