# CLAUDE.md

Public contributor guidance for AI coding assistants working in this repository.

## Project at a glance

**CCX (Chaos Cypher eXchange)** is an open, JSON-LD-native package format for
**portable, source-backed knowledge graphs**. A `.ccx` file is a ZIP that is,
semantically, an **RDF Dataset** — a `knowledge` default graph plus any number of
namespaced named graphs (the one extension mechanism). This repository is the
format **specification** plus the reference **reader + writer**, published to PyPI
as `ccx-format` (`import ccx`).

- `spec/` — the normative specification (Markdown, RFC-2119). *(in development)*
- `src/ccx/` — the reference reader + writer (Apache-2.0).
- `conformance/` — fixture packages (valid + deliberately invalid) for self-testing.
- `tests/` — the test suite.

## Working rules

1. **Search before adding** new helpers or patterns; prefer existing utilities.
2. **Storage-agnostic.** The library operates only on `.ccx` bytes and an in-memory
   JSON-LD / `rdflib` representation. It MUST NOT assume or touch any backend
   (SQLite, Postgres, a triplestore, files). Applications own their own mapping.
3. **Reader hardening is mandatory** for any code that reads untrusted packages:
   defend against decompression ("zip bomb") attacks, path traversal / absolute
   paths, symlink escape, and MUST NOT fetch remote JSON-LD contexts at read time.
4. **Spec ⇄ implementation ⇄ fixtures.** Every normative MUST is backed by a
   reference-implementation behavior *and* a conformance fixture.
5. **Add or update tests** for behavior changes.
6. **Permissive licensing only.** The spec is CC-BY-4.0, the code is Apache-2.0;
   dependencies must be OSI-approved permissive (no source-available / vendor
   lock-in).
7. Use **Conventional Commits**: `type(scope): subject`.

## Common commands

```bash
pip install -e ".[dev]"     # install with dev dependencies
pytest                      # run the test suite
ccx inspect  <pkg.ccx>      # show manifest + graph/asset registry
ccx validate <pkg.ccx>      # validate a package (exit non-zero on failure)
ccx pack <dir> -o <pkg.ccx> # assemble a .ccx from a prepared directory
```

## Documentation

- `README.md` — install and overview.
- `spec/` — the normative format specification.
- `conformance/README.md` — the conformance fixture suite.
