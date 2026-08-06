---
name: panopticon-interface-naming
description: >-
  Judge canonical interface names for the Panopticon index and persist the judgment as
  panopticon-interface hint comments. Apply when extracting or indexing interfaces, when two
  entries might denote the same interface under different names, when a CI check failed with an
  "add a hint" instruction, or whenever a naming decision for the index is needed.
---

# Panopticon interface naming and matching

See `docs/hint-reference.md` for the full hint syntax reference (every `panopticon-<hint>` form,
placement rules, exact behavior) — this skill covers the judgment behind `panopticon-interface`
specifically, not the general hint mechanism.

Canonical names make the whole index work: two entries are the same interface only when their
canonical names and `type` agree. Judgment layers strictly in this order:

1. **Hints win.** A `panopticon-interface <name>` comment in a file referencing the interface
   pins the canonical name. Never override a hint; if a hint is wrong, change the hint.
2. **Normalization rules next.** Lowercase; whitespace, `_`, `.`, `/`, `:` become `-`; dash runs
   collapse; leading/trailing dashes drop (`panopticon.naming.normalize_name`). If the normalized
   raw name is a good canonical name, use it — no judgment needed.
3. **LLM judgment last, and only locally.** When rules are inconclusive — lexically different
   names for the same interface, implementation identifiers that need a meaningful name, or
   ambiguous matches — judge. In CI there is no judgment: an unresolvable name fails the check
   and instructs the developer to add a hint locally.

## Judging a name

- During local documentation generation, read the instance repo's compiled index
  (`interfaces/index.json`) before minting a new name. Use the existing canonical name when source
  and configuration evidence show the same system, data, endpoint, topic, or contract — the
  **existing canonical name wins**, even when the raw names are lexically distant.
- Prefer organization-scale names based on durable technology and function, never an implementation
  identifier (`prod_topic_v2_final`), environment marker, team prefix, or bare generic such as
  `api`, `events`, or `config`:
  - shared infrastructure uses `<technology>-<function>` (`kafka-order-events`);
  - repo-local service surfaces use `<durable-repo-owner>-<surface>` (`orders-api`);
  - distinct contracts on one backend get distinct contract names.
- Do not maintain a generic-name warning list or blacklist. If the inferred raw name is generic,
  choose a meaningful organization-scale name during this judgment and persist it as a hint.
- Names are environment-free: `orders-api`, never `orders-api-staging` (see the
  panopticon-index-schema skill — code state, not deployment state).

The instance index is context for local judgment, not a replacement for code evidence. If the
index contains a possible match but the source and configuration cannot establish whether the
contracts are the same, stop and ask the user. Never choose a cross-repository name merely for
lexical symmetry or aesthetic consistency.

## CI candidate comparison

The PR workflow may provide a bounded set of child/instance candidates for advisory explanation.
For each candidate, classify it as `likely-same`, `likely-distinct`, or
`insufficient-evidence`, and cite the concrete source/configuration evidence present in the
provided entries. Return the requested structured result only. This comparison never edits a hint,
index, merge result, or gating outcome; deterministic merge simulation remains authoritative.

## Persisting the judgment

Every judgment MUST be written back as a hint comment in the code or configuration file that
references the interface, on or directly above the declaring line, using that file's comment
syntax:

```properties
# panopticon-interface order-events
topic=order.events
```

Hints never go into index files themselves. Once the hint exists, extraction resolves the name
deterministically on every future run — locally and in CI — which is what keeps shard merges and
pre-merge simulation reproducible.

## Existing docs that contradict the code

While exploring the repo you may find documentation — a README, architecture doc, or reference/
fixture doc — describing interfaces this repo doesn't actually have (e.g. it names config or
source files that were never committed). Never invent index entries, hint comments, or config to
match what a doc merely describes; name only what has real evidence in source/config files (see
panopticon-interface-extraction). When the doc is simply stale relative to the code, proceed with
naming what's actually there and leave the doc's revision to panopticon-doc-generation (see that
skill's drift-resolution rule). When it's unclear whether the gap is stale documentation or
unfinished implementation — nothing in the repo tells you which — stop and ask the user before
proceeding, rather than guessing which one it is.
