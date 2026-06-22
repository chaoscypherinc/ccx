// Load the BUILT package under real Node ESM *and* CJS to catch bad deep imports
// (e.g. an extensionless `ajv/dist/2020`) that bundler test resolvers tolerate but
// Node's native resolver rejects. Run after `npm run build`.
import { createRequire } from "node:module";

const esm = await import("../dist/index.js");
if (typeof esm.openPackage !== "function") {
  console.error("smoke FAILED: ESM build does not export openPackage");
  process.exit(1);
}

const require = createRequire(import.meta.url);
const cjs = require("../dist/index.cjs");
if (typeof cjs.openPackage !== "function") {
  console.error("smoke FAILED: CJS build does not export openPackage");
  process.exit(1);
}

console.log("smoke OK: ESM + CJS builds load under Node and export openPackage");
