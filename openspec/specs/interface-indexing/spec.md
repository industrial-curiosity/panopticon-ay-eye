# Interface Indexing Spec

## Purpose

Define the deterministic local, shard, and compiled interface-index lifecycle,
including canonical naming, validation, extraction, merging, and conflicts.

## Requirements

### Requirement: Index schema

Index files SHALL be JSON documents carrying a `schema_version` field and a map
keyed on **interface name** (a
meaningful name based on the interface's use or function). Each key SHALL map to
an array of interface objects,
each representing a single interface and all of its related info, with: `owner`
(repo and component, or `null`
for unknown/manually created infrastructure), `type` (e.g. `kafka`, `rest`,
`grpc`, `s3`), and `consumer` and
`producer` — each a list of repo objects holding the repo name and that repo's
array of source files that
create the interface or configure instances of it. Local indexes and shards
SHALL use the same schema; their
`consumer`/`producer` lists mention only the repo itself, and the compile step
unions the lists across shards.

#### Scenario: Valid entry round-trips

- **WHEN** a parser emits an interface entry for a REST endpoint owned by the
  repo
- **THEN** the local index contains a keyed entry with owner set to the
  repo/component, `type: "rest"`, and
  the repo listed in `producer` with the defining source files in its repo
  object

#### Scenario: Schema version present

- **WHEN** any index file (local, shard, or compiled) is written
- **THEN** it contains the current `schema_version`

### Requirement: Code-state semantics

The index SHALL describe the state declared by code on a given branch.
Environments (prod/staging/etc.) MUST
NOT appear as index dimensions, keys, or entry variants; environment-specific
configuration is visible only
indirectly through the source-file arrays of the repo objects.

#### Scenario: Multi-environment configuration

- **WHEN** a repo configures the same Kafka topic for prod and staging in two
  config files
- **THEN** the index contains one entry for the topic whose repo object lists
  both config files in its
  source-file array, with no environment field or per-environment entries

### Requirement: Name normalization and matching

Interface names SHALL be canonicalized by deterministic normalization rules
combined with LLM judgment guided
by the bundled skills, applied through the user's agent locally; in CI, names
SHALL resolve from hints and
normalization rules alone. Canonicalization SHALL happen when entries are
produced or merged (extraction, PR
simulation, shard merge), so that shards store canonical names and the
compiled-index rebuild remains a
deterministic union with no LLM involvement. Two entries SHALL be treated as the
same interface only when
their canonical names and `type` agree; anything less falls to conflict
detection.

Naming judgments SHALL be persisted as **hints**: `panopticon-`-prefixed
comments in the code or configuration
files where the interface is referenced (e.g. `# panopticon-interface &lt;name&gt;`) —
never in the index files
themselves. Extraction SHALL honor hints before applying normalization rules or
LLM judgment, so repeated runs
are deterministic. The local agent writes a hint whenever it makes a naming
judgment; a CI evaluation that
cannot resolve a name from hints and normalization rules SHALL fail the check
with an instruction to add the
hint.

#### Scenario: CI cannot resolve a name

- **WHEN** a PR changes an interface whose canonical name cannot be resolved
  from hints or normalization rules
- **THEN** the check fails, instructing the developer to add a
  `panopticon-interface` hint

#### Scenario: Hint pins the canonical name

- **WHEN** a source file carries `# panopticon-interface order-events` next to a
  topic declaration
- **THEN** extraction uses `order-events` as the canonical key with no LLM
  judgment

#### Scenario: Lexically different names for the same interface

- **WHEN** two repos declare the same Kafka topic under lexically different
  names
- **THEN** normalization and LLM matching resolve both entries to one canonical
  key before their shards are
  written, and the compiled index contains a single entry for the topic

#### Scenario: Compile stays deterministic

- **WHEN** the compiled index is rebuilt from shards
- **THEN** no LLM call is made; entries are unioned by their already-canonical
  keys

### Requirement: Type changes create a new interface object

An interface object SHALL be identified by its canonical name and `type`. When a
repo changes an interface's
type, it SHALL remove its repo objects from the original interface object and
add them to a new object under
the same key with the new type; the original object remains for any other repos
still using it.

#### Scenario: One repo migrates a shared interface's type

- **WHEN** two repos share an interface and one changes its type (e.g. `rest` to
  `grpc`)
- **THEN** the key holds two interface objects — the original type listing the
  unchanged repo, and the new
  type listing the migrating repo — and the split is visible in the instance
  repo

### Requirement: Empty entries are removed

An interface object SHALL be removed entirely when removing a repo leaves both
its `consumer` and `producer`
lists empty, and a key SHALL be removed from the index when its array of
interface objects becomes empty.

#### Scenario: Last repo stops using an interface

- **WHEN** a merge removes the only repo referenced by an interface object
- **THEN** the object is removed, and the key disappears from the compiled index
  if no other objects share it

### Requirement: Deterministic parser framework

The tooling SHALL provide a parser registry where each parser is a
self-contained Python module exposing
`detect(repo_root)` and `extract(repo_root)`, registered by interface type.
Extraction SHALL run every parser
whose `detect` returns true. Parsers MUST NOT import org-specific code or
require dependencies beyond the core
tooling's requirements. Before parser detection or extraction, shared file
iteration SHALL apply the analysis-scope policy. A parser that supports
declaration-level annotations SHALL preserve the candidate declaration line so
the shared analysis-scope filter can exclude that declaration.

#### Scenario: Parser handles its interface type

- **WHEN** extraction runs on a repo containing an OpenAPI specification
- **THEN** the REST parser detects it and emits index entries derived from the
  specification

#### Scenario: Parser skips an illustrative specification

- **WHEN** an OpenAPI specification is under `examples/`
- **THEN** interface extraction does not emit an entry from that file and
  reports its illustrative-directory exclusion

### Requirement: LLM extraction fallback with parser-gap reporting

Extraction SHALL fall back to the LLM for candidate interfaces not covered by
any deterministic parser —
through the user's agent locally and the agent runtime in CI. In CI, LLM
evaluation SHALL be scoped to what
changed plus the minimal context required to understand it; full-repo extraction
happens locally through the
user's agent. LLM-extracted entries SHALL be tagged `"extracted_by": "llm"`, and
the workflow summary SHALL
include a warning recommending creation of a deterministic parser for each
interface type extracted this way. Analysis scope SHALL filter candidate files
and annotated declarations before the LLM prompt is assembled.

#### Scenario: Unparsed interface type found

- **WHEN** extraction finds a message-queue interface for which no parser is
  registered
- **THEN** the LLM extractor emits the entry tagged `"extracted_by": "llm"` and
  the workflow summary recommends
  generating a parser for that interface type

#### Scenario: Ignored fallback declaration is omitted

- **WHEN** an otherwise eligible fallback file contains an annotated ignored
  declaration
- **THEN** the LLM prompt omits the annotation and declaration, and no extracted
  interface names that declaration

### Requirement: Interface extraction honors analysis scope

Interface extraction SHALL exclude files in exact illustrative directory components and files with
an early `panopticon-ignore file` annotation before parser detection or LLM fallback. Parsers SHALL
retain declaration-line metadata when available so a `panopticon-ignore declaration` annotation on
the declaration or immediately preceding line excludes only that candidate. Summaries SHALL report
excluded paths or declaration locations without exposing unrelated file contents.

#### Scenario: Production near-match remains indexed

- **WHEN** a Kafka declaration is in `src/sample-service/kafka.properties`
- **THEN** extraction retains the declaration because `sample-service` is not an exact excluded
  directory component

### Requirement: Shard merge and compiled index

The instance repo SHALL store one shard per repo (`interfaces/{repo}.json`) and
a compiled org-wide index
(`interfaces/index.json`). Merging a repo's index SHALL replace that repo's
shard wholesale, then rebuild the
compiled index deterministically from all shards. The compiled index MUST NOT be
edited in place by tooling.

#### Scenario: Repo re-asserts its interfaces

- **WHEN** a repo's merge workflow submits its local index
- **THEN** the repo's shard file is replaced with the submitted content and the
  compiled index is rebuilt from
  all shards

#### Scenario: Compiled index is reproducible

- **WHEN** the compiled index is rebuilt twice from the same shards
- **THEN** the outputs are byte-identical

### Requirement: Conflict detection

When merging or simulating, the tooling SHALL match incoming entries against
existing entries per the name normalization and matching requirement. A clear
match SHALL add or update the repo's objects in the interface's
`consumer`/`producer` lists. Entries without a clear match SHALL produce a
**conflict entry** in the instance
repo's `conflicts` array, recomputed deterministically on every compiled-index
rebuild. Local repo indexes
MUST NOT contain conflict entries — a repo only knows what it knows; conflicts
are registered and visible only
in the instance repo, where CI agents (and future visualizations) consume them.
All conflicts SHALL be
reported in the CI summary.

#### Scenario: Consumer matches an existing interface

- **WHEN** a repo consumes an interface that another repo owns and the entries
  clearly match
- **THEN** the merged entry lists the repo in `consumer` with its source files
  and no conflict is created

#### Scenario: Ambiguous match creates a conflict entry

- **WHEN** an incoming entry cannot be clearly matched to an existing object —
  the naming judgment is
  inconclusive, or two repos claim ownership of the same interface
- **THEN** a conflict entry is added to the instance repo's `conflicts` array
  and reported in the CI summary

### Requirement: Potential same-name interface collisions

The compiled interface index SHALL contain one deterministic
`potential-name-collision` conflict when interface objects sharing a canonical
name use different types and their participating repository sets are disjoint.
The conflict SHALL identify the canonical name, every involved type and
repository, and that it is a potential rather than confirmed semantic conflict.
The compiler SHALL recompute this conflict on every rebuild without an LLM call.
Local indexes and instance shards SHALL NOT contain this conflict.

#### Scenario: Disjoint repository sets use different types under one name

- **GIVEN** one repository uses `order-processing-queue` as `rest` and another
  repository uses it as `sqs`, with no participating repository in common
- **WHEN** the compiled index is rebuilt
- **THEN** it contains one `potential-name-collision` conflict for
  `order-processing-queue` that identifies both types and repositories

#### Scenario: A type migration overlaps a participating repository

- **GIVEN** same-name interface objects of different types share at least one
  participating repository
- **WHEN** the compiled index is rebuilt
- **THEN** it does not create a `potential-name-collision` conflict solely from
  that type difference

#### Scenario: A shard change removes the potential collision

- **GIVEN** a compiled index contains a `potential-name-collision`
- **WHEN** a shard update removes the disjoint type mismatch and the index is
  rebuilt
- **THEN** the derived conflict is absent from the rebuilt compiled index

### Requirement: Organization-aware judgments preserve deterministic indexes

Local organization-aware naming judgments SHALL be persisted as source or
configuration hints before extraction writes a shard. Extraction, PR
simulation, shard merge, and compiled-index rebuild SHALL resolve those hints
deterministically and SHALL not require access to the instance index or an LLM
to reproduce the stored result.

#### Scenario: Repeated extraction after a local naming judgment

- **WHEN** local documentation generation has persisted a canonical-name hint
  after consulting the instance index
- **THEN** a later local or CI extraction produces the same canonical key using
  the hint without an LLM call or a second instance-index comparison
