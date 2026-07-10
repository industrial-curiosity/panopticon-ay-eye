---
name: panopticon-interface-naming
description: >-
  Judge canonical interface names for the Panopticon index and persist the judgment as
  panopticon-interface hint comments. Apply when extracting or indexing interfaces, when two
  entries might denote the same interface under different names, when a CI check failed with an
  "add a hint" instruction, or whenever a naming decision for the index is needed.
---

# Panopticon interface naming and matching

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

- Prefer a **meaningful name based on use or function** (`order-events`), never an
  implementation identifier (`prod_topic_v2_final`), environment marker, or team prefix.
- Before minting a new name, check the instance repo's compiled index (`interfaces/index.json`)
  for an existing interface this one should match — same system, same data, same endpoint means
  the **existing canonical name wins**, even if lexically distant.
- Names are environment-free: `orders-api`, never `orders-api-staging` (see the
  panopticon-index-schema skill — code state, not deployment state).

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
