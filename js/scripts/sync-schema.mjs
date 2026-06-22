import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../src/ccx/schemas/manifest.schema.json");
const dst = resolve(here, "../src/schema/manifest.schema.json");
mkdirSync(dirname(dst), { recursive: true });
copyFileSync(src, dst);
console.log(`synced ${src} -> ${dst}`);
