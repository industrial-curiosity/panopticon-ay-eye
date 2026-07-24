# 2026 07 15 Init Dependency Steps Proposal

## Why

`panopticon-init` orchestrates exactly four steps — interface naming, interface
extraction, doc
generation, finalization — and never invokes `panopticon-dependency-naming` or
`panopticon-dependency-extraction`, even though both skills exist and the
`dependency-indexing`
capability is fully specified. Every repo initialized through the documented
`/panopticon-init`
flow today produces no dependency index at all: the org diagram and generated
docs are missing
cross-repo library-dependency edges from the moment a repo comes online, and a
maintainer only
discovers this by noticing the gap, not from any failure signal. This was
flagged as a real
template gap in feedback from a downstream instance
(`docs/action-plans/init-dependency-steps.md`).

## What Changes

- `panopticon-init`'s step order grows from four steps to six: interface-naming
  →
  interface-extraction → **dependency-naming → dependency-extraction** →
  doc-generation →
  finalization. The two new steps sit after interface extraction (a
  `panopticon-dependency-of`
  hint links a dependency entry to an existing interface's canonical name, so
  the interface index
  must already exist) and before doc-generation (which renders from the compiled
  indices,
  including the dependency shard).
- The checkpoint log (`panopticon/.init-log.json`) tracks two additional step
  ids
  (`dependency-naming`, `dependency-extraction`) so an interrupted-and-resumed
  run picks up
  correctly across the now six-step sequence.
- Each of the six skills remains independently invocable on its own, exactly as
  the existing four
  are today — this is a pure orchestration change, no skill's own behavior
  changes.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `repo-initialization`: the "Orchestrating init skill" requirement currently
  specifies a fixed
  four-step order and four checkpoint-log step ids; this changes to six steps
  and six step ids,
  with new scenarios covering the two inserted steps' position and resume
  behavior. The
  "Agent-driven initialization" requirement's Phase 2 description ("sequences
  the interface-naming,
  interface-extraction, and doc-generation skills") also needs to name the two
  new steps.

## Impact

- `.agents/skills/panopticon-init/SKILL.md`: step order, checkpoint log step-id
  list, and the
  "Determining the instance slug" / "Running" sections' cross-references.
- `openspec/specs/repo-initialization/spec.md`: "Orchestrating init skill" and
  "Agent-driven
  initialization" requirements and their scenarios.
- No changes to `panopticon-dependency-naming`,
  `panopticon-dependency-extraction`, or the
  `dependency-indexing` capability itself — both skills are already fully
  specified and this
  change only wires an existing call site.
- No changes to `panopticon/init_repo.py` finalization logic — finalization
  already validates
  documentation/index state generically and does not need to know about the
  dependency index
  specifically to keep working.
