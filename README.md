# ccx-format

```
pip install ccx-format   # → import ccx
```

**CCX (Chaos Cypher eXchange)** is the package format for portable, source-backed
knowledge graphs — sources, entities, relationships, and citations in a single
`.ccx` file. It is the format behind Lexicon packages in
[Chaos Cypher](https://github.com/chaoscypherinc/chaoscypher).

This repository is the future home of the **standalone CCX reader** — an
Apache-2.0 licensed library for reading `.ccx` packages without installing
Chaos Cypher. The current PyPI release is a placeholder reserving the name;
the format specification and this reader are in active development. Watch
this repo to be notified when the reader lands.

- Chaos Cypher (the format ships here today): https://github.com/chaoscypherinc/chaoscypher
- Docs: https://chaoscypher.com

Until the reader ships, `.ccx` import/export is available in Chaos Cypher itself.
