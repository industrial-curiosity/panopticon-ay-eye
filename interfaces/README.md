# Interface index

This directory holds the org-wide interface index in an instance repo:

- `{repo}.json` — one **shard** per child repo. A shard is replaced wholesale when its repo merges
  to main; never edit another repo's shard.
- `index.json` — the **compiled** org-wide index, rebuilt deterministically from all shards after
  every shard update. Never edited in place by tooling; its `conflicts` array is recomputed on
  every rebuild.

Humans may hot-fix a shard here in an emergency, but such edits are temporary by design: the
owning repo's next merge overwrites them (the owning repo is the source of truth).

In the template repo this directory is empty apart from this file — shards appear in instances as
child repos are initialized and merge.
