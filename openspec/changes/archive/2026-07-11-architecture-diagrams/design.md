# 2026 07 11 Architecture Diagrams Design

## Context

Panopticon already splits documentation work along a hard line: agent judgment
for prose that requires
understanding intent (`architecture.md`, `components/*.md`, `operations.md`),
and deterministic Python for
anything mechanically derivable from structured data (`interfaces.md` from the
local index, `compile_index()`
from shards). Diagrams fall on both sides of that line depending on scope:

- A **per-repo** diagram (this repo's internal components and how they relate)
  requires the same judgment as
  the rest of `architecture.md` — an LLM has to look at the code and decide
  what's a component and how data
  flows between them.
- An **org-wide** diagram (which repos talk to which, via which interfaces) is
  just a rendering of data the
  compiled index already has — `owner`, `producer`, `consumer` per interface
  entry. No judgment required.

This design keeps that split explicit rather than treating "architecture
diagram" as one feature with one
implementation.

Three existing CI touchpoints anchor the new behavior: `panopticon-pr.yml`
(per-PR checks, reads the instance
repo's config and skills), `panopticon-merge.yml` (merge-to-main sync, runs
`compile_index()` today via
`panopticon.merge merge`), and `sync-from-template.yml` (instance-repo-triggered
`git merge` of template
changes, today a blind merge with manual conflict resolution as the only
protection for instance-customized
files).

## Goals / Non-Goals

## Goals

- Per-repo architecture diagrams generated as part of doc-generation,
  drift-checked like the rest of
  `architecture.md`.
- A deterministic PR check that a diagram section exists and is structurally
  well-formed.
- A deterministic, always-current org-wide relationship diagram rebuilt on every
  merge to main, showing
  cross-repo interface relationships only (no internal-only interfaces), with a
  working navigation path from
  org diagram to each child repo's diagram and back.
- Diagram format configurable per instance, defaulting to Mermaid, protected
  from template sync overwrite.

## Non-Goals

- Rendering formats other than Mermaid are not implemented in this change — the
  config schema allows other
  values so orgs aren't locked in, but choosing one is a hard failure ("unknown
  diagram format") rather than
  a silent no-op, since building a second renderer with no requester is scope
  we're not taking on speculatively.
- In-diagram clickable nodes — GitHub does not reliably support Mermaid's
  `click` directive (CSP blocks it).
  Navigation uses ordinary markdown links instead.
- Solving org-diagram scale beyond "one markdown file, one section per repo." At
  genuinely thousands of
  interconnected repos this file could hit GitHub's render limits; that's a real
  ceiling this design pushes
  off, not one it removes.
- Generalizing the protected-config primitive to migrate *existing*
  protected-by-convention files
  (`panopticon.config.json`) onto the new mechanism. Diagram config is the first
  and only registry entry this
  change adds; `panopticon.config.json` keeps its current
  merge-and-manually-resolve behavior.

## Decisions

### D1: Diagram lives in a dedicated `## Architecture diagram` section, not folded into `Data flow`

`architecture-template.md`'s existing `Data flow` section already permits "a
short ordered narrative or a text
diagram," but that's optional prose an agent may or may not produce — not
something a deterministic checker
can reliably locate. The existence check and the org-diagram-link-back both need
a fixed, predictable anchor.
**Decision**: add a new required top-level section, `## Architecture diagram`,
containing exactly one fenced
code block tagged with the configured format's language identifier (``
```mermaid `` by default) directly
under that heading. `Data flow` keeps its narrative role unchanged.

*Alternative considered*: repurpose `Data flow`'s existing text-diagram
allowance. Rejected — "somewhere in
this prose section, maybe" isn't a stable target for either the existence check
or a stable link anchor.

### D2: Diagram-existence check is deterministic and separate from doc-drift

**Decision**: extend `panopticon.docs.validate_docs()` with a check that
`architecture.md` contains the
required section and a fenced block in the configured format; wire it as a new
step in `panopticon-pr.yml`
alongside doc-drift, index-currency, and simulation. It needs the instance repo
checked out first (to read the
diagram-format config), so it runs after that step, but it makes no LLM call and
needs no `PANOPTICON_LLM_*`
secrets.

Diagram *accuracy* (does the diagram still reflect the code?) is doc-drift's
job, not this check's — the
`panopticon-doc-drift` skill's judgment scope extends to cover the diagram
section the same way it already
covers the rest of `architecture.md`, producing the same kind of stale-doc
reason entry, not a new check
type.

*Alternative considered*: fold existence into doc-drift (let the LLM notice a
missing diagram). Rejected —
existence is mechanically checkable and doesn't need judgment or an LLM call;
keeping it deterministic keeps
it cheap, fast, and immune to LLM false negatives/positives, consistent with the
project's hybrid-execution
principle.

### D3: Org diagram is deterministic, rebuilt inline in the existing merge path

**Decision**: a new `panopticon/diagrams.py` module renders the org diagram from
a compiled index document —
pure function, same shape as `render_interface_docs()`. `merge_into_instance()`
(`panopticon/merge.py`) calls
it immediately after `compile_index(shards)` produces the new compiled state,
writing the result to
`docs/architecture.md` at the **instance repo root** (distinct from
`docs/{repo}/architecture.md`, which is
each child repo's own copy) — so there's exactly one, obviously-the-entry-point
location. No new workflow
step: it rides the same commit `panopticon-merge.yml` already produces for the
compiled index.

*Alternative considered*: a separate scheduled/periodic job. Rejected — the
rebuild is cheap and purely
derived from data the merge step already computes in memory; doing it inline
keeps it exempt from
doc-drift by construction (it cannot disagree with the index that produced it)
rather than needing a
freshness check of its own.

### D4: Org diagram document shape — alphabetical per-repo sections, ego-graph + table

**Decision**: one `## {repo}` section per repo with any external interface,
sorted alphabetically, each
containing (a) a small Mermaid graph with this repo as the center node and one
node per other repo it has an
external relationship with, edges labeled by interface name, and (b) a markdown
table below it with one row
per external interface: name, type, direction (produces/consumes relative to
this repo), the other repo, and
its role (owner/producer/consumer). Repos with no external interfaces are
omitted entirely.

**Internal-only exclusion rule** (mechanical): for a given interface entry,
compute
`repo_set = {owner.repo if owner} ∪ {r.repo for r in producer} ∪ {r.repo for r
in consumer}`. The entry is
*external* for repo X, and included, only when `len(repo_set) > 1` and `X in
repo_set`. An entry whose
`repo_set` is `{X}` alone (X produces and consumes its own interface, or owns it
with no other repo involved)
is internal-only and never appears in the org diagram.

Diagram edges are per-interface (not deduplicated across multiple interfaces to
the same other repo) —
Mermaid renders parallel edges without trouble, and the table is the exhaustive
source of detail, so the
diagram only needs to convey which repos relate, not enumerate every interface
visually.

*Alternative considered*: one org-wide graph with every repo as a node. Rejected
per the proposal discussion
— unreadable past a handful of repos, and doesn't compose with "click to see a
repo's own diagram" since
click-through doesn't work on GitHub anyway; per-repo sections with a table give
useful detail at any org
size (modulo the file-size ceiling noted in Non-Goals).

### D5: Navigation is plain markdown links, not diagram click-through

Confirmed by research (GitHub Community discussions #46096, #106690): GitHub's
Mermaid renderer blocks
`click`-to-URL navigation via CSP, and this is a known, currently-unresolved
platform limitation, not
something this change can work around. **Decision**: each org-diagram repo
section's table links each
"other repo" cell to that repo's `docs/{repo}/architecture.md` in the instance
repo; each child repo's
`## Architecture diagram` section gets a one-line "See the org diagram:
`{instance-repo-url}/docs/architecture.md#{repo}`"
link, written by doc-generation from `panopticon/config.json`'s already-known
`instance` field — no new
config needed for the back-link.

### D6: Diagram format config is a new protected file, not a new field in `panopticon.config.json`

**Decision**: `panopticon.diagram.config.json` at the instance repo root, schema
`{"format": "mermaid"}`,
default `mermaid` when absent. Kept as its own file rather than a new key in the
existing org config
(`gating`, `workflow_ref`) because it needs fundamentally different sync
treatment: protected from
`sync-from-template`'s merge entirely, versus `panopticon.config.json`'s current
behavior (merged, conflicts
resolved manually). Git's protection mechanisms (merge drivers,
`.gitattributes`) operate per-path, not
per-JSON-field, so mixing the two into one file would either force the *whole*
org config to become
sync-protected (silently changing `gating`/`workflow_ref` behavior, never asked
for) or require bespoke
field-level merge logic in place of standard git tooling.

### D7: General protected-config primitive: registry + path-level protection + field-diff warning

**Decision**: a small registry in `panopticon/config.py` (or a new
`protected_config.py`) — e.g.
`PROTECTED_CONFIG_FILES = {"panopticon.diagram.config.json": {"format":
"mermaid"}}` — mapping protected
paths to their template-shipped default content. `sync-from-template.yml` gains
two behaviors driven by this
registry:

1. **Protection**: registered paths are excluded from the template merge so the
   instance's version always
   wins, regardless of what the template ships.
2. **Field-diff warning**: before/during sync, compare the *incoming* template
   version's top-level JSON keys
   against the instance's current file's keys for each registered path; when
   they differ (template added or
   removed a field), emit a non-blocking `::warning::` naming the file and the
   field difference, so an org
   owner notices "the template added a new diagram-config option you haven't
   set" without it being silently
   applied or silently missed.

The registry itself is ordinary Python — it travels through normal template sync
like any other code, so
adding a second protected config later is a registry entry plus a
`.gitattributes` line, not a new mechanism.

*Alternative considered*: scope this to diagram config only (no registry,
one-off special case in the
workflow). Rejected per explicit product direction — the general primitive costs
little extra now and avoids
redoing the mechanism for the next instance-local setting.

**Resolved by spike** (see Open Questions): `.gitattributes merge=ours` engages
correctly in both
`sync-from-template.yml` paths — first-sync (`--allow-unrelated-histories -X
theirs`, no common ancestor) and
routine-sync (default strategy, common ancestor) — but only when the workflow
explicitly runs
`git config merge.ours.driver true` as a step before `git merge`. The driver's
command is git config, not
versioned content, so `.gitattributes` alone (declaring
`panopticon.diagram.config.json merge=ours`) is not
sufficient by itself; the workflow must register the driver locally on every
run. Confirmed empirically: without
the `git config` step, `-X theirs` overwrote the instance's customized file with
the template's; with the step,
the instance's file was untouched in both merge paths, and appeared in neither
the diff nor a conflict.

### D8: New gating check type `diagram-missing`, default blocking

**Decision**: add `diagram-missing` to `panopticon.config.py`'s
`CHECK_TYPES`/`DEFAULT_GATING`, defaulting to
`blocking` — same default rationale as `init`/`doc-drift`: it's deterministic
(no LLM false-positive risk),
so a failure is always actionable and blocking-by-default matches those checks
rather than
`interface-conflict`'s advisory-by-default (which exists specifically to absorb
LLM false positives).

## Risks / Trade-offs

- **[Risk]** Existing repos have no diagram section yet; the moment
  `diagram-missing` ships as blocking by
  default, every open PR in every already-initialized repo starts failing until
  that repo runs doc-generation
  once to backfill it. → **Mitigation**: this is exactly what the existing
  gating config lever is for — call
  this out explicitly in the migration plan (org owners can set
  `diagram-missing: advisory` in
  `panopticon.config.json` during rollout, flip to `blocking` once repos have
  backfilled), rather than
  inventing new rollout machinery.
- **[Risk]** `.gitattributes merge=ours` behavior under
  `sync-from-template.yml`'s unrelated-histories
  first-sync path is unverified. → **Mitigation**: spike against a sandbox
  instance repo before committing to
  it in tasks.md; documented fallback if it doesn't hold — skip the git merge
  driver entirely and instead
  script the protection as an explicit post-merge step (checkout the instance's
  pre-merge version of each
  registered path over whatever the merge produced, before committing).
- **[Risk]** GitHub Mermaid rendering could change its `click`/CSP behavior over
  time (the platform issue is
  actively tracked upstream, not permanently settled). → **Mitigation**: none
  needed now since the design
  doesn't depend on click working; if GitHub later supports it reliably,
  click-through can be added later as
  a pure enhancement without changing the table-based navigation this design
  relies on.
- **[Trade-off]** Per-interface (non-deduplicated) edges in the per-repo
  mini-diagram can look visually noisy
  for repo pairs with many shared interfaces. Accepted for v1 — the table
  carries the authoritative detail;
  revisit if real org diagrams turn out unreadable in practice.
- **[Risk]** Org diagram document size at large org scale (Non-Goals). → No
  mitigation in this change; flagged
  as a known ceiling.

## Migration Plan

1. Ship the new `## Architecture diagram` section requirement,
   `panopticon-doc-generation` skill update, and
   `panopticon.diagram.config.json` default (`mermaid`) — additive, no existing
   behavior breaks.
2. Ship the `diagram-missing` PR check and doc-drift's extended scope with
   `diagram-missing` defaulted to
   `advisory` at first in the template's own default (even though D8 reasons
   toward `blocking` long-term) —
   org owners opt into `blocking` once their repos are backfilled, exactly
   mirroring how a brand-new
   blocking-by-default check would otherwise break every existing repo's next PR
   with no warning.
3. Ship the org-diagram rebuild in `master-sync` — safe to enable immediately,
   purely additive output, no
   dependency on child repos having backfilled anything (repos with no diagram
   section yet simply don't
   affect the org diagram, which is index-derived, not diagram-section-derived).
4. Ship the protected-config primitive and `sync-from-template.yml` changes
   last, after the git-merge-driver
   spike (see Open Questions) resolves the implementation approach.
5. Rollback: each piece is independently revertable (skill update, one workflow
   step, one config default) —
   no data migration, no schema version bump to the index or compiled index.

## Open Questions

- ~~Does a `.gitattributes`-registered `merge=ours` driver engage during
  `sync-from-template.yml`'s first-sync
  path?~~ **Resolved**: yes, in both the first-sync and routine-sync paths,
  provided the workflow runs
  `git config merge.ours.driver true` before merging (the driver command lives
  in git config, not
  `.gitattributes`, so it must be set locally on every run — it cannot be
  shipped as versioned content alone).
  Group 7 uses this `.gitattributes` + `git config` approach, not the
  post-merge-restore fallback.
- ~~Should `diagram-missing` ship `blocking` or `advisory` by default?~~
  **Resolved** by the pr-evaluation
  spec's "Org-configurable gating" requirement: `advisory` by default (Migration
  Plan's rollout reasoning),
  same as the `DEFAULT_GATING` value tasks.md group 4.1 implements.
- Exact registry shape for D7 (module location, whether the field-diff warning
  also needs to detect *value*
  drift for specific fields the template cares about, vs. field-*name* drift
  only as currently scoped) —
  left for tasks.md/implementation to settle against the real
  `panopticon/config.py` structure.
