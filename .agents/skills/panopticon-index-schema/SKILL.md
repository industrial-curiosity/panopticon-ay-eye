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
appears indirectly via the source-file array of an entry. Never add
per-environment keys, entry variants, or filters.

## Structure

- The index is keyed on the **interface name**: a meaningful name based on
  the interface's use or function, not an implementation identifier.
- Each key maps to an **array of interface objects** with:
  - `owner` — repo and component; `null` if unknown or manually created
    infrastructure.
  - `consumer` / `producer` — booleans describing this repo's relationship.
  - `type` — e.g. `kafka`, `rest`, `grpc`, `s3`.
  - `sources` — array of source files (files creating the interface and
    files configuring instances of it).

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

- Consumer of an external interface: look for an existing entry; on a clear
  match, ensure consumer/producer flags are correct; otherwise add a
  **conflict entry**.
- Owner of an interface: look for an existing entry; on a clear match, check
  for inaccuracies; otherwise add a conflict entry.
- Conflict entries are always logged and surfaced in the CI summary (and PR
  comment during pre-merge simulation). Whether they block is org
  configuration — see
  [panopticon-architecture](../panopticon-architecture/SKILL.md).
