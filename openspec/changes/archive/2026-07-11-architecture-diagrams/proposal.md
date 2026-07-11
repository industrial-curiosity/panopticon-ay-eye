## Why

Panopticon's four documentation layers describe a repo's purpose, components, interfaces, and operations in
prose, but nothing visualizes the relationships — within a repo, or across the org. A developer reading a PR
comment about an interface conflict has no picture of what actually talks to what, and an org owner has no
single place to see how repos relate short of reading every `interfaces.md`. Architecture diagrams close that
gap: agent-drawn per-repo component diagrams generated alongside the rest of doc generation, a deterministic
PR check that they exist, and a deterministic org-wide relationship diagram rebuilt from the compiled index on
every merge to main — mirroring the project's existing split between agent judgment (prose, per-repo diagrams)
and deterministic derivation (`interfaces.md`, the compiled index, and now the org diagram).

## What Changes

- Doc generation gains a diagram section in each repo's `architecture.md`: an agent-drawn component/data-flow
  diagram in the org's configured format (default Mermaid), following the same "ground every statement in the
  code" discipline as the rest of the layer.
- The doc-drift check's scope extends to judge diagram staleness the same way it judges prose staleness — the
  diagram is part of the architecture-overview layer, not a separate check.
- A new deterministic PR check verifies the diagram section exists and is well-formed (parses as a fenced
  block in the configured format) — existence/structure only, independent of and in addition to doc-drift's
  accuracy judgment.
- The merge-to-main sync workflow gains a deterministic org-diagram rebuild step, run alongside the existing
  compiled-index rebuild: one document in the instance repo with one section per repo (alphabetical), each
  showing that repo's cross-repo relationships as a small diagram plus a table of its external interface
  links (owner/producer/consumer), excluding interfaces with no cross-repo edge. No LLM involvement — the
  content is mechanically derived from the compiled index, so it can never disagree with it (same reasoning
  as `interfaces.md`), and it is therefore exempt from doc-drift checking.
- Diagram tooling/format is configurable per instance repo (default `mermaid`), stored in a new protected
  config file that the template's `sync-from-template` workflow never overwrites. This introduces a general
  "protected instance-local config" primitive — a registry of `{path, template default}` pairs that
  `sync-from-template` excludes from its merge and instead field-diffs (template's field set vs. instance's)
  to warn when the template introduces or removes a field the instance hasn't picked up. Diagram config is
  the first entry in that registry.
- No node-level click-through inside diagrams: GitHub's Mermaid renderer does not reliably support `click`
  navigation (content-security-policy blocks it). Cross-repo and org↔child navigation uses ordinary markdown
  links in tables/prose instead.

## Capabilities

### New Capabilities

- `architecture-diagrams`: owns the diagram content contract (what a per-repo diagram must show, the org
  diagram's document shape and the internal-only-interface exclusion rule, the diagram-format configuration
  schema and its default) that `doc-generation`, `pr-evaluation`, and `master-sync` each hook into at their
  own trigger points — mirrors how `interface-indexing` owns index schema/semantics that other capabilities
  consume.

### Modified Capabilities

- `doc-generation`: architecture-overview layer gains a required diagram section; doc-drift's judgment scope
  extends to cover diagram staleness alongside prose staleness.
- `pr-evaluation`: adds a new deterministic diagram-existence check to the PR workflow's check set and
  combined report/gating contract.
- `master-sync`: adds a deterministic org-diagram rebuild step to the merge-to-main sync, alongside the
  existing compiled-index rebuild.
- `repo-initialization`: `sync-from-template`'s "Template update workflow" requirement gains the general
  protected-config-with-field-diff-warning mechanism.

## Impact

- **Code**: `panopticon/docs.py` (diagram section in architecture-overview handling, existence validation),
  `panopticon/merge.py` (org-diagram rebuild alongside `compile_index`), `panopticon/config.py` (protected
  config registry, diagram config schema/defaults), a new `panopticon/diagrams.py` (or similar) for
  deterministic org-diagram rendering from the compiled index.
- **Skills**: `panopticon-doc-generation` (diagram section rules), `panopticon-doc-drift` (diagram-staleness
  judgment).
- **Workflows**: `.github/workflows/panopticon-pr.yml` (new existence-check step), `panopticon-merge.yml`
  (org-diagram rebuild step), `sync-from-template.yml` (protected-config exclusion + field-diff warning).
- **New files**: a diagram-config file at the instance repo root (protected from sync), a `.gitattributes`
  entry for the protected-config merge behavior, the org diagram document in the instance repo.
- **No breaking changes** to the index schema or existing check gating defaults; diagram checks need their
  own gating entries (advisory/blocking), extending `panopticon.config.json`'s `gating` map.
