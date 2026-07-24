# Interface Indexing Spec

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
tooling's requirements.

#### Scenario: Parser handles its interface type

- **WHEN** extraction runs on a repo containing an OpenAPI specification
- **THEN** the REST parser detects it and emits index entries derived from the
  specification

### Requirement: LLM extraction fallback with parser-gap reporting

For candidate interfaces not covered by any deterministic parser, extraction
SHALL fall back to the LLM —
through the user's agent locally and the agent runtime in CI. In CI, LLM
evaluation SHALL be scoped to what
changed plus the minimal context required to understand it; full-repo extraction
happens locally through the
user's agent. LLM-extracted entries SHALL be tagged `"extracted_by": "llm"`, and
the workflow summary SHALL
include a warning recommending creation of a deterministic parser for each
interface type extracted this way.

#### Scenario: Unparsed interface type found

- **WHEN** extraction finds a message-queue interface for which no parser is
  registered
- **THEN** the LLM extractor emits the entry tagged `"extracted_by": "llm"` and
  the workflow summary recommends
  generating a parser for that interface type

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
existing entries per the name
normalization and matching requirement: a clear match adds or updates the repo's
objects in the interface's
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
