# Dependency Indexing Spec

## Requirements

### Requirement: Dependency index schema

Dependency index files SHALL be JSON documents carrying a `schema_version` field
and a map keyed on
**canonical dependency name** (the package/module identity, e.g. a Go module
path or a package coordinate).
Each key SHALL map to an array of dependency objects, each with: `ecosystem`
(e.g. `go`, `java`, `python`,
`npm` — an open, non-empty string, not a fixed enum, matching the
interface-indexing capability's `type`
field's freedom), `owner` (the self-registered publisher's repo and component,
or `null` when no repo has
self-registered as producer yet), `producer` and `consumer` — each a list of
repo objects holding the repo
name and that repo's array of source files. Consumer repo objects MAY
additionally carry `apis`: a
deduplicated, sorted list of the specific modules/packages that repo imports
from the dependency
(import-level granularity — not call-site or symbol-level). A dependency object
MAY carry
`links_to_interface`: `{"name": ..., "type": ...}`, set only via the
`panopticon-dependency-of` hint (see
"Interface-linking hint"). This capability's files are entirely separate from
the interface-indexing
capability's `interfaces/` files — dependencies are never recorded as an
interface `type`.

#### Scenario: Valid entry round-trips

- **WHEN** a parser emits a dependency entry for an internal Go module imported
  by a repo
- **THEN** the local index contains a keyed entry with `ecosystem: "go"`, the
  repo listed in `consumer` with
  its source files, and (when import scanning succeeds) an `apis` list of the
  imported subpackage paths

#### Scenario: Consumer entry without resolvable imports

- **WHEN** a parser identifies a repo as depending on an internal package but
  cannot determine which modules
  it imports (e.g. no import-scanning support for that ecosystem yet)
- **THEN** the consumer repo object is recorded with `source_files` populated
  and `apis` omitted, rather than
  failing extraction

### Requirement: Own shard and compiled files, separate from interfaces

The instance repo SHALL store one dependency shard per repo
(`dependencies/{repo}.json`) and a compiled
org-wide dependency index (`dependencies/index.json`), structurally parallel to
the interface-indexing
capability's shard/compiled-index lifecycle (merge replaces a repo's shard
wholesale, then rebuilds the
compiled index deterministically) but stored and merged independently of
`interfaces/`.

#### Scenario: Repo re-asserts its dependencies

- **WHEN** a repo's merge workflow submits its local dependency index
- **THEN** the repo's dependency shard file is replaced with the submitted
  content and the compiled
  dependency index is rebuilt from all dependency shards, with no effect on
  `interfaces/` files

### Requirement: Structural zero-configuration detection

Extraction SHALL resolve a dependency as internal deterministically, with no org
configuration and no
network lookup, whenever the ecosystem's dependency declaration already embeds
the org's own identity (e.g. a
Go module path under `github.com/{org}/...`, where `{org}` is read from the
instance repo's own `instance`
field).

#### Scenario: Go module path resolves without configuration

- **WHEN** a repo's `go.mod` requires a module whose path begins with the org's
  own GitHub organization
- **THEN** extraction records it as an internal dependency without consulting
  `internal_registries` or
  performing any lookup

### Requirement: Org-declared registry detection

The org config SHALL support an optional `internal_registries` field: a list of
non-empty host/URL substring
strings, defaulting to an empty list when omitted, validated the same way as the
existing `protected_paths`
field. A dependency whose manifest resolves it from a host matching one of these
entries SHALL be treated as
internal. The same field SHALL be consulted for both consumer-side detection and
producer-side
self-registration (see "Self-registration"), so an org configures its registry
identity once.

#### Scenario: Manifest resolves from a declared registry host

- **GIVEN** org config `internal_registries: ["packages.example.com"]`
- **WHEN** a repo's manifest declares a dependency resolved from
  `https://packages.example.com/...`
- **THEN** extraction records it as an internal dependency

#### Scenario: No registries configured

- **WHEN** org config omits `internal_registries`
- **THEN** it defaults to an empty list and registry-host detection contributes
  no matches, without error

### Requirement: Cross-reference the instance repo

For dependency candidates not resolved by structural or registry-host detection,
extraction SHALL check
whether the candidate's canonical name is already self-registered as a producer
in the instance repo's
compiled dependency index. In CI, this SHALL be a plain filesystem read of the
already-checked-out instance
repo — `panopticon-pr.yml`/`panopticon-merge.yml` already run a full
`actions/checkout` of the instance repo
before any check runs, the same precondition every other CI-side instance-repo
read in this codebase
(`load_org_config`, the compiled interface index) already relies on — so no live
API call and no new
authentication mechanism are needed there. Locally, where no instance checkout
is guaranteed, the agent
SHALL attempt the same read on a best-effort basis (a local checkout if present,
otherwise a live GitHub API
read using the same token-resolution precedent as `org_diagram_link.py`) and,
when unavailable, SHALL fall
through to hint/LLM resolution rather than blocking.

#### Scenario: Candidate matches an already-registered producer

- **WHEN** a consumer's dependency candidate isn't resolved by layers 1–2, and
  the instance repo's compiled
  dependency index (read from an available checkout, local or CI) already has a
  producer entry for that
  canonical name
- **THEN** extraction records the consumer against that entry without requiring
  a hint

#### Scenario: Local check unavailable falls through gracefully

- **WHEN** the local agent has no authenticated access to the instance repo and
  no local instance checkout
- **THEN** extraction proceeds to hint/LLM resolution instead of failing

### Requirement: Hint annotations and LLM extraction fallback

Dependency naming and internal/external judgments SHALL be persisted as hints,
mirroring the
interface-indexing capability's hint contract: `panopticon-dependency
&lt;name&gt;`-prefixed comments pin a
candidate's canonical name and internal status. Extraction SHALL honor hints
before structural rules,
registry-host matching, or instance cross-reference. For candidates no layer
resolves, extraction SHALL fall
back to the LLM (locally through the user's agent, in CI through the agent
runtime scoped to the diff),
tagging entries `"extracted_by": "llm"` and recommending, in the workflow
summary, that a deterministic
parser be contributed for that ecosystem or pattern when LLM extraction recurs.
A CI evaluation that cannot
resolve a candidate from any layer SHALL fail the check with an instruction to
add a `panopticon-dependency`
hint, matching the interface-indexing capability's "CI cannot resolve a name"
behavior.

#### Scenario: Hint pins a candidate the other layers miss

- **WHEN** a source file carries `# panopticon-dependency internal-metrics-lib`
  next to a dependency
  declaration that no structural, registry, or cross-reference layer resolved
- **THEN** extraction uses `internal-metrics-lib` as the canonical name with no
  LLM judgment

#### Scenario: Non-manifest declaration caught by LLM fallback

- **WHEN** a dependency is declared outside any manifest file (e.g. a generated
  pipeline job's runtime
  package-install parameter) and no parser covers that pattern
- **THEN** LLM extraction may still emit an entry tagged `"extracted_by":
  "llm"`, and the workflow summary
  recommends a deterministic parser for that pattern

#### Scenario: CI cannot resolve a candidate

- **WHEN** a PR changes a dependency candidate that no layer can resolve as
  internal or external
- **THEN** the check fails, instructing the developer to add a
  `panopticon-dependency` hint

### Requirement: Interface-linking hint

No naming heuristic SHALL infer a link between a dependency entry and an
interface entry automatically — it
SHALL only be set by an explicit `panopticon-dependency-of <interface-name>`
hint placed at the dependency's
declaration, using the same hint-scanning precedence already implemented for
interface hints
(comment-adjacent for text-based manifests, sibling-file precedence for
comment-less JSON manifests). When
set, the dependency object's `links_to_interface` field records the target
interface's name and type.

#### Scenario: Hint links a generated API client to its interface

- **WHEN** a source file carries `# panopticon-dependency-of
  order-processing-api` next to a dependency
  declaration for a generated REST client package
- **THEN** the resulting dependency entry's `links_to_interface` names
  `order-processing-api`, and no such
  link is created for any dependency without an explicit hint

### Requirement: Self-registration

A repo SHALL self-register as a dependency's producer when: for ecosystems with
no separate publish step
(e.g. Go, where the module path itself is the source of truth), its manifest
declares a module path under
the org's own identity; for registry-based ecosystems, its manifest declares
package coordinates *and* its
build or publish configuration targets a host listed in `internal_registries`. A
manifest name with no
corroborating publish evidence and no `panopticon-dependency` hint SHALL NOT
self-register a producer.

#### Scenario: Go repo self-registers from its module path alone

- **WHEN** a repo's `go.mod` module path is under the org's own GitHub
  organization
- **THEN** the repo self-registers as that module's producer with no further
  evidence required

#### Scenario: Registry-based repo needs both name and publish evidence

- **GIVEN** org config `internal_registries: ["packages.example.com"]`
- **WHEN** a repo's manifest declares a package name but its CI has no publish
  step targeting
  `packages.example.com` and no `panopticon-dependency` hint is present
- **THEN** the repo does not self-register as that package's producer

### Requirement: Two-phase extraction

Dependency extraction SHALL run in two phases: a manifest-scan phase that
determines whether a repo depends
on or publishes a candidate internal package, and a source-scan phase that
determines which specific
modules/packages a consumer actually imports from a resolved internal
dependency, populating `apis`. The
source-scan phase MAY be unimplemented for a given ecosystem's parser without
blocking manifest-scan results
— `apis` is optional per the dependency index schema requirement.

#### Scenario: Manifest-only parser still produces a valid entry

- **WHEN** an ecosystem's parser implements only manifest scanning
- **THEN** extraction still records consumer and producer entries with
  `source_files`, omitting `apis`

### Requirement: Conflict detection including unregistered producer

When merging or simulating, matching and conflict detection SHALL follow the
interface-indexing capability's
existing pattern (clear match updates producer/consumer lists; an ambiguous
match — e.g. two repos both
self-registering the same canonical name — produces a conflict entry with reason
`ownership-dispute`).
Dependency-indexing additionally defines a new conflict reason,
`unregistered-producer`: when a candidate
resolves as internal (via structural or registry-host detection) but no repo has
self-registered as its
producer, a conflict entry SHALL be created with this reason, recomputed on
every compiled-index rebuild and
reported in the CI summary, advisory by default.

#### Scenario: Internal candidate with no known producer

- **WHEN** a consumer's dependency candidate resolves as internal but the
  compiled dependency index has no
  producer entry for its canonical name
- **THEN** a conflict entry with reason `unregistered-producer` is added to the
  instance repo's `conflicts`
  array and reported in the CI summary

### Requirement: Empty entries are removed

A dependency object SHALL be removed entirely when removing a repo leaves both
its `consumer` and `producer`
lists empty, and a key SHALL be removed from the index when its array of
dependency objects becomes empty,
mirroring the interface-indexing capability's equivalent requirement.

#### Scenario: Last repo stops depending on a package

- **WHEN** a merge removes the only repo referenced by a dependency object
- **THEN** the object is removed, and the key disappears from the compiled
  dependency index if no other
  objects share it

### Requirement: Annotation reference documentation

Every dependency annotation form (`panopticon-dependency`,
`panopticon-dependency-of`) SHALL be documented in
a single written reference covering its syntax, placement, and effect, rather
than only existing as scattered
code comments — extending the same documentation gap already identified for
interface hints.

#### Scenario: Developer looks up an unfamiliar annotation

- **WHEN** a developer sees a `panopticon-dependency-of` comment in a manifest
  and doesn't know what it does
- **THEN** a single documented reference explains its syntax, placement, and
  effect
