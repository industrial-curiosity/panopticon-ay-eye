## Context

`interface-indexing` already indexes runtime interfaces (Kafka, REST, gRPC, S3) with a proven
shard-per-repo → compiled-index → conflict-detection lifecycle, a hint/LLM-fallback naming pattern, and a
self-contained parser registry. Internal (same-org) library/package dependencies are a different kind of
relationship — compile-time coupling, not a runtime protocol — but the cross-repo blast-radius problem they
create is the same shape, so this design reuses as much of that proven machinery as fits without bending the
interface schema's assumptions (owner/producer/consumer are about who serves/calls a protocol; a dependency
has exactly one publisher and many importers, and importers need to record *which* modules they actually
import, which no existing repo-object field captures).

Grounding for the detection design came from four real repos across three ecosystems (Go, JVM/Gradle,
Python/Poetry) plus two incidental finds (a generated Airflow DAG, a Backstage catalog). Findings that shaped
the decisions below:

- Go module paths embed the org identity (`github.com/{org}/...`) — detection needs zero configuration.
- JVM and Python in the reference org both resolved internal packages from the same private registry host —
  one config field can cover multiple ecosystems.
- Some "dependencies" were generated REST client SDKs for APIs already indexed as `rest` interfaces —
  the same relationship visible from two angles.
- Real dependency usage doesn't always flow through a standard manifest file (a Databricks job parameter
  named a Python package with no `requirements.txt`/`pyproject.toml` entry at all) — manifest parsing alone
  will not catch everything, by design, in any org.

## Goals / Non-Goals

**Goals:**
- Track internal dependencies as their own relationship, not a new `interface` type.
- Detection that works with zero configuration for self-describing ecosystems (Go) and minimal, portable
  configuration for registry-based ecosystems (JVM, Python, npm, ...) — no org-specific logic hardcoded into
  the tooling.
- Consumer entries record which specific modules/packages they import (import-level), not just that a
  dependency exists.
- Interfaces and dependencies render together on the org diagram, deduplicated when explicitly linked.
- Every annotation form is documented in one place, not scattered code comments.
- Gaps in automatic detection are catchable via hints, consistent with the existing interface-hint contract.

**Non-Goals:**
- Call-site/symbol-level analysis (e.g. "consumer calls `verify_token()` specifically"). Import-level
  granularity only, per the settled decision — a real static-analysis undertaking is out of scope here.
- Automatic reconciliation between a dependency and an interface it happens to wrap. No naming heuristic is
  trusted to do this safely across arbitrary orgs' codegen conventions; reconciliation is annotation-driven.
- Version-drift tracking (consumer pinned to an old version of a producer that has since changed). Real
  future value, not part of this change.
- A second parser for every ecosystem in this change. Go ships as the deterministic proof of concept; other
  ecosystems fall back to LLM extraction with parser-gap reporting until contributed, same as interfaces
  today.

## Decisions

**Own schema and files, not a new interface `type`.** `dependencies/{repo}.json` shards and
`dependencies/index.json` compiled, parallel to `interfaces/`, reusing the same `schema_version` /
deterministic-serialization conventions as `panopticon/index.py`. Keeps "interface" meaning one thing (a
runtime protocol) and lets dependency-specific concepts (single publisher, per-consumer import lists,
registry-host detection) evolve without stretching the interface schema's validation rules.

**Schema shape mirrors interfaces, with one new field.** Each dependency object:
`{"ecosystem": "go", "owner": {"repo": ..., "component": ...} | null, "producer": [...], "consumer": [...],
"links_to_interface": {"name": ..., "type": ...} | omitted}`. Repo objects keep `repo`/`source_files`
(and `extracted_by` where applicable); consumer repo objects additionally carry `apis`: a deduplicated,
sorted list of imported module/package paths. `ecosystem` (not `type`) names the field to signal it's a
different axis than interface protocol type, though it's validated the same way — a non-empty string, open
vocabulary, no fixed enum, exactly like `type` today.

**Two-phase extraction per repo.** Phase 1 (manifest scan) answers "does this repo depend on / publish an
internal package, and at what version" — the existing kind of extraction interface parsers already do.
Phase 2 (source scan) answers "which specific modules does this repo actually import from it" — genuinely
new: parsers additionally walk import statements in source files matching a resolved internal dependency,
populating `apis`. A dependency can be recorded from phase 1 alone if phase 2 finds nothing (e.g. an
ecosystem where the parser can't yet do import scanning) — `apis` is optional, not required, so partial
parser coverage degrades gracefully instead of failing.

**Detection layers, most portable first** (mirrors the interface-indexing hint/normalization/LLM pattern,
reapplied to a different question — "is this internal and who owns it" rather than "what's the canonical
name"):
1. **Structural, zero-config** — an ecosystem whose dependency declaration already embeds the org's GitHub
   identity (Go module paths under `github.com/{org}/...`, `{org}` read from the instance repo's own
   `instance` field) resolves deterministically, no config, no lookup.
2. **Org-declared registry host** — new optional org-config field `internal_registries` (list of host/URL
   substrings, validated the same way as the existing `protected_paths` field: non-empty strings, defaults to
   `[]`). A manifest resolving its dependency from a declared host is internal. This single field is reused
   for both consumer-side detection (does this look like ours) and producer-side self-registration (does our
   own publish step target one of these hosts) — one thing for an org to configure, not two.
3. **Cross-reference the instance repo, no checkout required** — for candidates layers 1–2 don't resolve,
   read the instance repo's compiled dependency index for a matching self-registered producer. In CI, this
   reuses the existing `PANOPTICON_INSTANCE_TOKEN` (already scoped for instance-repo read/write per the
   settled auth architecture) to do a single-file API read — no new auth mechanism. Locally, the agent
   best-effort attempts the same read (via an authenticated `gh`, or a local instance checkout if present)
   and, consistent with the existing tolerance for diagram-config reads with no local instance checkout,
   silently falls through to layer 4 rather than blocking when unavailable.
4. **Hint / LLM fallback** — reuses the existing hint-comment and LLM-extraction-with-parser-gap-reporting
   contract verbatim, just applied to dependency candidates instead of interface names. CI fails loudly with
   "add a hint" instructions when nothing resolves, matching the existing interface-indexing scenario.

**Self-registration mirrors consumer detection, using the same config.** A repo self-registers as a
producer when: (Go) its module path is under the org's GitHub identity — always, since Go has no separate
publish step, any tagged commit is installable; (registry ecosystems) its manifest declares a package
name/coordinates *and* its build/publish configuration targets a host in `internal_registries`. A manifest
name with no corroborating publish evidence and no hint is not enough on its own to self-register — avoids
false self-registration from, say, a `name` field on a package nobody actually ships anywhere internal.

**Reconciliation is annotation-driven, not heuristic.** No naming pattern (`-api-client-sdk`, `Client`,
generator-specific suffixes) is trusted as a universal "this dependency wraps that interface" signal —
codegen conventions vary too much across orgs and tools to guess safely, and a wrong guess silently
mislinks two unrelated things. Instead, a new hint form `panopticon-dependency-of <interface-name>`,
placed at the dependency declaration using the exact same hint-scanning mechanism already implemented for
interface hints (comment-adjacent for text formats, sibling-file precedence for comment-less JSON manifests),
sets `links_to_interface` on the dependency object. This is the "easy, so do it automatically" case
made lightweight — one hint, mechanically applied — rather than an automatic guess.

**New conflict category: unregistered producer.** A candidate resolves as internal (via layer 1 or 2) but no
repo has self-registered as its producer. This doesn't fit either existing conflict reason
(`ownership-dispute`, `owner-attribution-mismatch`) — it's genuinely new to dependency-indexing, since
interfaces never require an owner to exist (owner can legitimately be `null` for externally-owned infra) but
an *internal* dependency with no known internal producer is either a detection false-positive or a
not-yet-onboarded repo, and either way is worth surfacing. Reported the same way existing conflicts are:
recomputed on every compiled-index rebuild, advisory by default, visible in the CI summary.

**Diagram rendering: dependency edges alongside interface edges, deduplicated when linked.**
`architecture-diagrams`'s org diagram gains dependency edges rendered with the same repo-relationship-diagram
shape already used for interfaces, visually distinguished (e.g. dashed vs. solid — exact rendering left to
the diagram-format renderer, matching how the existing spec leaves Mermaid-vs-other-format specifics to the
renderer). When a dependency carries `links_to_interface` matching an interface entry between the same two
repos, the two collapse into one edge in the render, labeled as both — mechanical once the hint exists, not
a runtime guess.

## Risks / Trade-offs

- **`internal_registries` still requires an org to configure something.** → Acceptable: it's one field,
  optional, empty-by-default, and only needed for registry-based ecosystems — Go needs zero configuration,
  and orgs without a registry-based ecosystem never touch it.
- **Import-level `apis` can get noisy for repos with many small subpackage imports (as seen in the Go
  reference repo, 6 distinct subpackages from one dependency).** → Deduplicated and sorted at the repo-object
  level, same treatment as `source_files` today; no further filtering — a long-but-accurate list is more
  useful than an arbitrarily truncated one for the impact-analysis use case this exists for.
- **Manifest-only extraction misses non-manifest declarations (the Databricks job-parameter case).** →
  Accepted per the explicit decision to catch "as much as reasonable," not everything; hint annotations and
  LLM-extraction-with-parser-gap-reporting are the intended catch-all, same contract interfaces already rely
  on.
- **The instance cross-reference (layer 3) has no guaranteed availability locally.** → Matches existing
  precedent (diagram-config reads already tolerate "no local instance checkout available"); local judgment
  degrades gracefully to hints rather than blocking.
- **Two new hint forms add to what a developer needs to know.** → Mitigated by the explicit documentation
  requirement (one written reference covering every annotation, interface and dependency alike) rather than
  relying on tribal knowledge, closing a gap already flagged in `docs/explore/interface-name-collisions.md`
  for interface hints.

## Migration Plan

Purely additive: new files (`dependencies/{repo}.json`, `dependencies/index.json`), new optional org-config
field, new optional hint forms. No existing interface schema, file, or hint changes. Repos not yet running
the new parser/extraction logic simply have no dependency shard — same "absent means not yet onboarded"
semantics as a repo with no interface shard today. Rollout is per-repo as each repo's local tooling picks up
the new extraction step, no coordinated cutover required.

## Open Questions

- Which ecosystem ships the first deterministic parser after Go — JVM (registry-host detection, higher
  payoff given the generated-client-SDK overlap with REST interfaces) or Python (simpler manifest, but the
  reference org's real usage bypassed the manifest entirely)? Left for `tasks.md` sequencing / a follow-up
  contribution, not blocking this change's core mechanism.
- Exact rendering treatment for a dependency `links_to_interface` pointing at an interface name that no
  longer exists (interface removed, hint gone stale) — likely a conflict-detection case similar to existing
  stale-reference handling, but not fully specified here.
