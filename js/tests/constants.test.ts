import { expect, test } from "vitest";
import * as C from "../src/constants";

test("constants match the reference reader", () => {
  expect(C.MIMETYPE).toBe("application/vnd.ccx+zip");
  expect(C.CCX_VERSION).toBe("3.0");
  expect(C.MAX_ENTRIES).toBe(100_000);
  expect(C.MAX_ENTRY_UNCOMPRESSED).toBe(512 * 1024 * 1024);
  expect(C.MAX_TOTAL_UNCOMPRESSED).toBe(2 * 1024 * 1024 * 1024);
  expect(C.SOURCE_MODES).toEqual(["embedded", "referenced", "derived-only"]);
});
