# 2026 07 14 Track Internal Dependencies Proposal

## Why

Panopticon currently indexes runtime interfaces (Kafka, REST, gRPC, S3) but has
no way to represent
compile-time/library coupling between org repos — one repo importing another org
repo's published package.
That coupling is real cross-repo blast radius (`docs/planned-work.md`: "Track
internal dependencies") that
today is invisible to conflict detection, doc generation, and the org diagram
alike.

## What Changes

- New `dependency-indexing` capability: tracks internal (same-org)
  library/package dependencies as their own
  first-class relationship, separate from runtime interfaces — a producer repo
  self-registers the package(s)
  it publishes, and each consumer repo registers itself with the specific
  modules/packages it imports from
  that dependency (import-level granularity, not just "depends on X").
- Layered, config-light detection so this generalizes beyond any single org's
  conventions:
  - Structural, zero-config: ecosystems whose dependency declarations already
    embed the org identity (e.g.
    Go module paths under the org's GitHub org) resolve deterministically with
    no configuration.
  - Org-declared registry hosts: a new, optional org-config field
    (`internal_registries`) lets an org name its
    own private package registry host(s) once; any ecosystem resolving a
    dependency from a declared host is
    treated as internal.
  - Cross-reference against the instance repo's self-registered producers via a
    live read (no local checkout
    required), for candidates the above two layers don't resolve.
  - Hint annotations and LLM extraction fallback (mirroring the existing
    interface-hint/LLM-fallback pattern)
    for anything else, so gaps are catchable rather than silently missed — with
    CI failing loudly, not
    silently, when a candidate can't be resolved by any layer.
- New annotation forms, each documented in a single written reference (not
  scattered code comments):
  `panopticon-dependency` (pin a canonical dependency name) and
  `panopticon-dependency-of` (declare that a
  dependency entry is the packaged/client form of an existing interface entry,
  enabling reconciliation).
- `architecture-diagrams` (modified): the org diagram and per-repo diagram
  sections render dependency edges
  alongside interface edges, visually distinguished; a dependency linked to an
  interface via
  `panopticon-dependency-of` collapses to a single edge instead of two redundant
  ones.
- A first deterministic parser for Go module dependencies (the zero-config
  case), following the existing
  self-contained parser-registry pattern; other ecosystems (JVM, Python, npm,
  ...) are expected to be
  contributed the same way over time, falling back to LLM extraction with
  parser-gap reporting until then.

## Capabilities

### New Capabilities

- `dependency-indexing`: schema, shard/compile lifecycle, self-registration,
  detection layers, hint
  annotations, conflict handling, and documentation requirements for tracking
  internal (same-org) library
  dependencies as a relationship distinct from runtime interfaces.

### Modified Capabilities

- `architecture-diagrams`: org diagram and per-repo diagram sections must render
  dependency edges alongside
  interface edges, visually distinguished, with edge deduplication when a
  dependency is linked to an
  interface via annotation.

## Impact

- New Python modules mirroring the existing `panopticon/index.py` /
  `panopticon/merge.py` pattern for a
  parallel `dependencies/{repo}.json` shard and `dependencies/index.json`
  compiled index in the instance
  repo.
- New parser module (`panopticon/parsers/go_mod.py` or equivalent) added to the
  existing parser registry.
- `panopticon/config.py`: new optional `internal_registries` field on the org
  config, validated the same way
  as the existing `protected_paths` field.
- `panopticon/naming.py` (or a dependency-specific equivalent): new hint forms
  (`panopticon-dependency`, `panopticon-dependency-of`).
- `panopticon/diagrams.py` and the `architecture-diagrams` capability's
  rendering logic: combined
  interface+dependency rendering and edge deduplication.
- New written reference documenting every dependency annotation form (extends
  the existing gap already
  flagged for interface hints in `docs/explore/interface-name-collisions.md`).
- No changes to the existing `interfaces/` schema or files — dependencies are
  additive and live alongside,
  not inside, the interface index.
