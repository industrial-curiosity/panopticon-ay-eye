---
name: panopticon-dependency-naming
description: >-
  Judge whether a library/package dependency is internal (same-org) for the Panopticon dependency
  index, and persist the judgment as panopticon-dependency / panopticon-dependency-of hint
  comments. Apply when extracting or indexing dependencies, when a manifest entry's internality is
  ambiguous, when a CI check failed with an "add a hint" instruction, or when a dependency looks
  like it might be a packaged/client form of an existing interface.
---

# Panopticon dependency naming and internality judgment

See `docs/hint-reference.md` for the full hint syntax reference (every `panopticon-<hint>` form,
placement rules, exact behavior) — this skill covers the judgment behind `panopticon-dependency`
and `panopticon-dependency-of` specifically, not the general hint mechanism.

Dependency-indexing is a separate relationship from interface-indexing (see
panopticon-index-schema) — this skill covers internal (same-org) library/package dependencies,
not runtime interfaces. Judgment layers strictly in this order:

1. **Hints win.** A `panopticon-dependency <name>` comment pins the canonical name outright — used
   verbatim, **never normalized** (lowercased/dash-ified) the way an interface name is, since a
   dependency's raw name is already a machine identifier (a Go module path, a Maven
   `groupId:artifactId`, a PyPI/npm package name) and normalizing it would break exact matching
   against real import paths and registry coordinates.
2. **Structural, zero-config next.** Some ecosystems embed the org's own identity in the
   dependency declaration itself — a Go module path under `github.com/{org}/...` is unambiguous
   with no lookup needed. Prefer this whenever the ecosystem supports it.
3. **Org-declared registry host next.** Check the org config's `internal_registries` — does the
   manifest resolve this dependency from a host the org has declared as its own (an Artifactory,
   Nexus, or other private registry)?
4. **Instance cross-reference next.** Check whether the candidate's name is already self-registered
   as a producer in the instance repo's compiled dependency index (a live read when no local
   checkout is available — never guessed, never blocking if unavailable).
5. **LLM judgment last, and only locally.** When none of the above resolve it — no naming
   convention or registry match, no existing self-registration — judge from context: does this
   package's name, source (e.g. a private/internal-looking registry URL), or surrounding project
   conventions suggest it belongs to this org? An ambiguous case is better left unreported than
   reported wrong. In CI there is no judgment: an unresolvable candidate fails the check and
   instructs the developer to add a hint locally.

## Judging self-registration (producer side)

- A repo self-registers as a dependency's producer when its own manifest's name/module-path is
  under the org's identity (Go: always, no further evidence needed) or, for registry-based
  ecosystems, when the manifest's own name/coordinates are corroborated by a publish step
  targeting a declared `internal_registries` host. A bare `name` field with no publish evidence
  and no hint is not enough — don't self-register speculatively.

## Judging the interface link (`panopticon-dependency-of`)

- Some dependencies are packaged/generated clients for a runtime interface this org already
  indexes (e.g. a generated REST client SDK for an API another repo owns). **Never infer this
  link from naming conventions alone** — `-api-client-sdk`-style suffixes, generator-specific
  class names, and similar patterns vary too much across orgs and toolchains to trust as a
  universal signal, and a wrong guess silently mislinks two unrelated things.
- Only set the link when there's real evidence: the dependency's own docs/README say what API it
  wraps, the package is clearly a generated client for an interface this repo (or another repo you
  can verify) already owns, or the developer confirms it directly.
- Persist a confirmed link as `# panopticon-dependency-of <interface-name>` next to the dependency
  declaration, naming the interface's canonical name exactly as it appears in the interface index.

## Persisting the judgment

Every judgment MUST be written back as a hint comment in the code or configuration file that
references the dependency, on or directly above the declaring line, using that file's comment
syntax:

```go
// panopticon-dependency-of order-processing-api
require github.com/acme/orders-api-client v1.0.0
```

Hints never go into index files themselves. Once the hint exists, extraction resolves the name
and any interface link deterministically on every future run — locally and in CI.

## Relationship to interface hints

A repo may carry both `panopticon-interface`/`panopticon-dependency` hints in the same file tree —
they are independent vocabularies (different `panopticon-<hint>` prefixes) and never conflict.
Don't reuse an interface hint to describe a dependency, or vice versa, even when they're adjacent
in the same manifest.
