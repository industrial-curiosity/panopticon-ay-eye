# Organization-aware interface naming design

## Context

The local index currently derives an interface name from an adjacent hint or
normalizes its raw declaration. That makes repeated extraction deterministic,
but it can preserve generic names that are meaningful only in one repository.
The instance compiled index is already downloaded in pull-request workflows and
used by deterministic merge simulation, but local documentation generation has
no required organization-index preflight. As a result, a child can commit a
locally sensible index whose same-type entries silently combine after merge.

## Goals / Non-Goals

**Goals:**

- Make local documentation generation use the instance index before it creates
  or refreshes a local interface index.
- Infer organization-scale names and persist those judgments as source or
  configuration hints that users can review and override.
- Show a prominent, visual prospective-merge result on every evaluated PR.
- Let the instance select the default interface-conflict policy and the child
  repository select an explicit, committed override.

**Non-Goals:**

- Let CI rename interfaces, alter hints, or resolve conflicts automatically.
- Replace deterministic extraction, merge simulation, or conflict detection
  with an LLM.
- Maintain a blacklist or an advisory warning set of generic words.
- Change merge-time synchronization or allow PR workflows to alter the
  instance default branch.

## Decisions

### Documentation generation owns the organization-aware naming preflight

Before it refreshes the local index or renders index-derived documentation, the
documentation-generation phase SHALL retrieve the compiled interface index from
the configured instance's default branch. It uses a locally available instance
checkout when supplied; otherwise, it retrieves the single compiled-index file
using the configured instance identity and authenticated GitHub access. A
missing index in a fresh instance is treated as an empty valid compiled index.
An unavailable or invalid existing index stops the preflight with an actionable
recovery instruction; it does not fall back to inventing an unreviewed generic
name.

The preflight invokes the existing local interface-naming and extraction flow,
then renders documentation from the resulting local index. This preserves the
current deterministic renderer while placing the user-requested organization
context in the phase that produces the documentation. The prior initialization
ordering remains valid: the doc-generation invocation performs its preflight
after its ordinary extraction prerequisites, and can update hints plus rerun
extraction before rendering.

### Naming is evidence-led and hints remain the user override

The local agent uses the declaration, configuration, ports, imports, and the
instance candidate entries to decide whether an interface already exists or
needs a new canonical name. Existing compatible interface names win only where
the evidence identifies the same actual contract. Otherwise it creates a
non-generic canonical name:

- Shared durable infrastructure uses `<technology>-<function>`.
- A repo-local service surface uses `<durable-repo-owner>-<surface>`.
- Distinct contracts on one transport or backend use distinct contract names.

The agent writes the result as an adjacent `panopticon-interface` hint and
regenerates the local index. A hint always wins, is never silently rewritten,
and is the only supported user override. Genericity is a contextual naming
judgment, not a hard-coded warning vocabulary or string blacklist.

### PR analysis separates judgment from merge truth

Provider workflows continue to download the instance compiled index and run
the existing deterministic simulation. A new bounded candidate-comparison step
prepares relevant same-type and name-similar instance entries for the CI LLM,
along with the proposed child index and changed evidence. The LLM labels a
candidate as a likely same interface, likely distinct interface, or insufficient
evidence, and explains the evidence. It cannot change the index, hint, merge
result, or gate outcome.

The PR report combines this advisory analysis with the deterministic simulation
result. Exact simulation conflicts remain the source of truth; candidate matches
and semantic near-misses are visible recommendations for the contributor to run
local documentation generation and commit a reviewed hint.

### Mermaid visibility is added to the maintained report comment

The existing marker-owned Panopticon PR comment, not the author-controlled PR
body, includes the child architecture overview's validated Mermaid block under
a dedicated prospective-architecture heading. The same report includes
candidate analysis and deterministic merge findings. This keeps a single
updatable report without overwriting author content. A malformed or unavailable
diagram is reported through the existing diagram check and is represented as an
explicit unavailable state rather than fabricated Mermaid.

### Child gating overrides instance gating

`gating.interface-conflict` keeps `advisory` as its built-in default. The
instance's `panopticon.config.json` supplies an organization default. The child
repository's committed `panopticon/config.json` can supply a validated override
for that one check. The effective order is child override, instance value, then
built-in default. The workflow makes the resolution visible in its report.

Both modes produce the same prominent warning. `advisory` allows the workflow
to pass after the warning; `blocking` fails the interface-conflict check so
branch protection can prevent merge.

## Risks / Trade-offs

- [Instance index is unavailable during local generation] → Stop before naming
  and give the exact configured instance/index recovery path; use an empty index
  only when the instance genuinely has no compiled index.
- [A large instance index exceeds CI context limits] → Deterministically narrow
  candidates by type and name similarity before the LLM call, and retain full
  deterministic simulation independently.
- [An LLM mistakes a semantic near-match for a match] → Treat the result as
  advisory explanation only; local evidence and a reviewed hint remain required.
- [Existing child repositories contain generic names] → Migrate in controlled
  child PRs: run the preflight, review generated hints/index changes, inspect
  advisory simulation results, and merge incrementally.
- [A child weakens a safety policy] → Make the override explicit, committed,
  validated, and conspicuous in the PR report; instances can still set their
  preferred default for repositories without an override.

## Migration Plan

1. Add the configuration parser, naming guidance, preflight retrieval, and
   deterministic tests without changing existing index keys automatically.
2. Add CI candidate reporting, Mermaid embedding, and effective-policy display
   across all provider workflows.
3. Enable the default advisory policy. Child repositories opt into blocking by
   committing their override after validating their existing index.
4. Inventory existing generic names through controlled child documentation
   refresh PRs, commit reviewed hints and regenerated shards, and use the
   prospective merge report to sequence changes.
5. Roll back by removing a child override or reverting its hints/index change;
   deterministic merge behavior and the instance default remain intact.

## Open Questions

None. The chosen policy is child-owned override over an instance default, with
an advisory built-in default and a prominent warning in either mode.
