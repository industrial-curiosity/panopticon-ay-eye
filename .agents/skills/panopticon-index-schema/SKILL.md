---
name: panopticon-index-schema
description: >-
  Semantics and schema rules for the Panopticon interface index. Apply when
  designing, generating, merging, validating, simulating, or documenting the
  interface index — local repo indexes, instance-repo shards, or the compiled
  org index — and when writing parsers or extraction logic that emits index
  entries. Fires for any work touching index files, entries, or their schema.
---

# Interface index schema rules

## Code state, not deployment state

The index describes the state declared by code. **Branches are a first-class
dimension; environments (prod/staging/etc.) are not.** Do not model
environments as index dimensions — environment-specific configuration only
appears indirectly via the source-file arrays of an entry's repo objects.
Never add per-environment keys, entry variants, or filters.

## Structure

- The index is keyed on the **interface name**: a meaningful name based on
  the interface's use or function, not an implementation identifier. Names
  are canonicalized by deterministic normalization rules plus LLM judgment
  (via skills) at extraction/merge time — never at compile time, so the
  compiled rebuild stays a deterministic, LLM-free union of shards. Naming
  judgments are persisted as `panopticon-`-prefixed hint comments in the
  code or configuration files where the interface is referenced (e.g.
  `# panopticon-interface <name>`) — never in index files; extraction honors
  hints before rules or LLM judgment.
- Each key maps to an **array of interface objects**, one per interface with
  all of its related info:
  - `owner` — repo and component; `null` if unknown or manually created
    infrastructure.
  - `type` — e.g. `kafka`, `rest`, `grpc`, `s3`.
  - `consumer` / `producer` — lists of repo objects, each holding the repo
    name and that repo's array of source files (files creating the interface
    and files configuring instances of it).
- Local indexes and shards use the same schema; their `consumer`/`producer`
  lists mention only the repo itself, and the compile step unions the lists
  across shards.

## Storage layout

- Each child repo maintains its own local index and is authoritative for
  interfaces it owns.
- The instance repo stores one **shard per repo** plus a **compiled**
  org-wide index rebuilt after every shard update. Re-assertion by a repo is
  a whole-shard replace, never an in-place edit of the compiled index.
- Branch state maps to instance-repo branches: PR workflows push a repo's
  docs and index state to a branch named `{repo}/{branch}` in the instance
  repo. The instance repo's default branch holds only merged (main) state.

## Matching and conflicts

- Matching compares canonical names and `type`; where hints and normalization
  rules alone cannot decide whether two entries denote the same interface,
  the LLM judges via the user's agent locally. In CI a name that cannot be
  resolved from hints and rules fails the check with an instruction to add a
  hint — LLM naming judgment happens only locally.
- An interface object is identified by canonical name + `type`. A type change
  is a **new object**: the changing repo removes its repo objects from the
  old element and adds them to a new element under the same key; the old
  element remains for other repos still using it.
- On a clear match, add or update the repo's objects in the
  `consumer`/`producer` lists; entries without a clear match (inconclusive
  naming, disputed ownership) become **conflict entries**.
- If removing a repo from an object empties both its `consumer` and
  `producer` lists, remove the object entirely; a key with no objects left
  is removed from the index.
- Conflict entries exist only in the instance repo — the compiled index's
  `conflicts` array, recomputed deterministically on every rebuild. Local
  repo indexes never contain conflicts; a repo only knows what it knows.
- Conflict entries are always logged and surfaced in the CI summary (and PR
  comment during pre-merge simulation). Whether they block is org
  configuration — see
  [panopticon-architecture](../panopticon-architecture/SKILL.md).
