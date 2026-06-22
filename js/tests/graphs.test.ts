import { expect, test } from "vitest";
import { rejectRemoteContext, isDefault } from "../src/graphs";
import { CcxSecurityError } from "../src/errors";

test("rejects a top-level remote @context string", () => {
  expect(() => rejectRemoteContext({ "@context": "https://evil/ctx" })).toThrow(
    CcxSecurityError,
  );
});

test("rejects a remote @import nested anywhere", () => {
  expect(() => rejectRemoteContext({ x: { "@import": "http://evil" } })).toThrow(
    CcxSecurityError,
  );
});

test("allows a local @context with a node-scoped object and an empty @graph", () => {
  expect(() =>
    rejectRemoteContext({ "@context": ["./local", { foo: "bar" }], "@graph": [] }),
  ).not.toThrow();
});

test("isDefault is true for the explicit default role", () => {
  expect(isDefault({ role: "default", namespace: "x" })).toBe(true);
});

test("isDefault is true for the reserved ccx namespace", () => {
  expect(isDefault({ namespace: "ccx" })).toBe(true);
});

test("isDefault is false for an arbitrary namespace with no default role", () => {
  expect(isDefault({ namespace: "acme" })).toBe(false);
});
