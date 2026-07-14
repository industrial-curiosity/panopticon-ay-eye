# Parser contribution guide

Deterministic parsers are how Panopticon's interface coverage grows. When the LLM extraction
fallback tags entries `"extracted_by": "llm"`, the workflow summary recommends creating a parser
for that interface type — this guide is the follow-through. Parsers born inside an org's instance
repo should be contributed upstream to this template so every org benefits.

This guide covers **interface parsers** (`INTERFACE_TYPE`, registered in `panopticon.parsers.REGISTRY`).
**Dependency parsers** (dependency-indexing capability — internal same-org library/package
dependencies, e.g. `panopticon/parsers/go_mod.py`) follow the same self-contained
`detect(repo_root)`/`extract(repo_root)` shape and the same rules below, but emit `DEPENDENCY_ECOSYSTEM`
instead of `INTERFACE_TYPE` and a differently-shaped candidate (see `go_mod.py`'s module docstring),
registered in `panopticon.dependency_extraction.DEPENDENCY_REGISTRY` (a separate registry from
interfaces') rather than in `REGISTRY` above. The LLM fallback and parser-gap reporting exist
end-to-end for dependencies too — `panopticon.dependency_extraction.llm_extract`, guided by the
`panopticon-dependency-extraction` skill, tags entries `"extracted_by": "llm"` the same way the
interface fallback does. This section is deliberately a summary, not the full contract table below
(candidate field names differ — see `go_mod.py`'s module docstring for the authoritative shape);
expanding it into its own full section is tracked, not yet done.

## The contract

A parser is **one self-contained Python module** in `panopticon/parsers/`, registered in
`REGISTRY` in `panopticon/parsers/__init__.py`, exposing:

```python
INTERFACE_TYPE = "kafka"          # the index `type` this parser emits

def detect(repo_root) -> bool:    # cheap: does this repo contain material for this parser?
    ...

def extract(repo_root) -> list:   # candidate entries (see below)
    ...
```

`extract` returns **candidates**, not index entries — the extraction driver resolves canonical
names and folds them into the index:

```python
{
    "raw_name": "order.events",       # the name exactly as found in the source
    "hint": "order-events" or None,   # panopticon-interface hint near the declaration, if any
    "type": INTERFACE_TYPE,
    "role": "producer" or "consumer",
    "source_file": "config/topics.yaml",  # repo-root-relative, posix separators
    "owned": True,                    # the repo declares/creates the interface
    "component": "order-service" or None,
}
```

Use the shared helpers: `panopticon.parsers.iter_files` (skips vendored/generated directories,
returns sorted paths — required for determinism), `panopticon.parsers.relative_posix`, and
`panopticon.naming.nearest_hint` / `interface_hints` for hint comments.

## Rules (enforced in review)

1. **Stdlib only.** No new dependencies — see `.agents/skills/panopticon-python-tooling`. If the
   format genuinely needs a third-party parser, a narrow line-wise scrape of the fields you need
   beats adding a dependency (see `rest_openapi._title_from_yaml`).
2. **Self-contained.** No imports from org-specific code, no shared mutable state, no network.
3. **Deterministic.** Same repo contents → same candidates in the same order. Sort anything that
   iterates the filesystem.
4. **Honor hints.** A `panopticon-interface` comment on or near a declaration pins its name; pass
   it through as `hint`.
5. **Fail soft on malformed files.** A file the parser cannot read or parse is skipped, never a
   crash — other parsers and the LLM fallback may still handle it.
6. **Narrow and documented scope.** State in the module docstring exactly which file
   names/shapes the parser reads and which role/ownership it assigns to each. A parser that does
   one shape well beats one that guesses at many.

## Tests

Add fixture files under `tests/fixtures/sample_repo/` (or a new fixture tree if detection would
clash) and a test class in `tests/test_parsers.py` covering detection, extraction of each
supported shape, role/ownership assignment, and hint handling. Run the suite with:

```bash
python3 -m unittest discover -t . -s tests
```

## Upstreaming

Open a PR against this template repo with the parser module, its registration, fixtures, and
tests. Describe the real-world configs it was validated against. Orgs carrying the parser in
their instance meanwhile can keep it in their instance's `panopticon/parsers/` — the module is
self-contained, so moving it upstream later is a file copy.
