/**
 * Exception hierarchy for the CCX reader.
 *
 * Mirrors the Python error taxonomy in `src/ccx/errors.py`:
 * - CcxError            -> CCXError (base class for all CCX reader errors)
 * - CcxValidationError  -> CCXValidationError (structurally / schematically invalid)
 * - CcxSecurityError    -> CCXSecurityError (unsafe: zip bomb, traversal, network)
 * - CcxIntegrityError   -> CCXIntegrityError (a checksum or signature did not verify)
 */

/** Base class for all CCX reader errors. */
export class CcxError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = "CcxError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/** The package is structurally or schematically invalid. */
export class CcxValidationError extends CcxError {
  constructor(message?: string) {
    super(message);
    this.name = "CcxValidationError";
  }
}

/** The package tried to do something unsafe (zip bomb, traversal, network). */
export class CcxSecurityError extends CcxError {
  constructor(message?: string) {
    super(message);
    this.name = "CcxSecurityError";
  }
}

/** A checksum or signature did not verify. */
export class CcxIntegrityError extends CcxError {
  constructor(message?: string) {
    super(message);
    this.name = "CcxIntegrityError";
  }
}
