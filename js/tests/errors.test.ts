import { expect, test } from "vitest";
import { CcxError, CcxValidationError, CcxSecurityError, CcxIntegrityError } from "../src/errors";

test("every CCX error subclasses CcxError", () => {
  expect(new CcxValidationError("x")).toBeInstanceOf(CcxError);
  expect(new CcxSecurityError("x")).toBeInstanceOf(CcxError);
  expect(new CcxIntegrityError("x")).toBeInstanceOf(CcxError);
});

test("CCX errors are also instances of Error and keep their name + message", () => {
  const e = new CcxValidationError("bad manifest");
  expect(e).toBeInstanceOf(Error);
  expect(e.name).toBe("CcxValidationError");
  expect(e.message).toBe("bad manifest");
});
