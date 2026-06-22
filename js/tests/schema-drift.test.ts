import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "vitest";

test("bundled manifest schema matches the Python source of truth", () => {
  const py = readFileSync(resolve(__dirname, "../../src/ccx/schemas/manifest.schema.json"), "utf8");
  const js = readFileSync(resolve(__dirname, "../src/schema/manifest.schema.json"), "utf8");
  expect(js).toBe(py);
});
