# Hint annotation reference

Panopticon resolves some judgments (a canonical name, whether something belongs to this org,
whether two things are the same relationship) from `panopticon-`-prefixed comments — **hints** —
rather than only from deterministic rules or LLM guesswork. A hint always wins over normalization
rules and LLM judgment (`panopticon/naming.py`), and hints never live in the index files
themselves — only in the source/config files that reference the thing being pinned.

This page documents every hint form that exists in the tooling today. It doesn't cover the
broader mental model (what an interface or dependency *is*, what each conflict category means) —
see `docs/setup-guide.md` for setup and `panopticon/index.py`/`panopticon/dependencies.py`'s module
docstrings for the schema itself.

## Syntax

All hints share one shape, regardless of comment style:

```
panopticon-<hint-name> <value>
```

- `<hint-name>` is lowercase letters, digits, and dashes.
- `<value>` is a single token (no spaces) — the canonical name or interface name being pinned.
- The comment marker before `panopticon-` doesn't matter — `#`, `//`, or any other prefix works
  identically, since the parser matches the `panopticon-<hint>` text itself, not the comment
  syntax of any particular language.
- Placement: **on the line above, or directly on, the declaration it pins** — hint resolution
  looks at most 2 lines above the target line (`panopticon/naming.py`'s `nearest_hint`, default
  `max_distance=2`). A hint further away, or in an unrelated part of the file, won't be picked up.

## `panopticon-interface <name>`

**Capability:** interface-indexing.
**Effect:** pins the canonical name for the interface (REST API, Kafka topic, etc.) declared or
referenced on the line below/at the hint.
**When to use it:** two repos use lexically different names for the same interface, or a
config/spec file's raw name (an implementation identifier, an auto-generated title) isn't a good
canonical name on its own.

```properties
# panopticon-interface order-events
topic=order.events
```

Without this hint, Panopticon derives the canonical name by lowercasing and dash-normalizing the
raw name found in the file (`panopticon/naming.py`'s `normalize_name`) — e.g. `order.events`
would normalize to `order-events` on its own in this example, so the hint here is only needed when
normalization alone wouldn't produce the name you want, or when two repos need to agree on one
name across lexically different raw values.

## `panopticon-dependency <name>`

**Capability:** dependency-indexing.
**Effect:** pins the canonical name for an internal (same-org) library/package dependency declared,
imported, or published on the line below/at the hint.
**When to use it:** a dependency isn't caught by any deterministic layer (a Go module path under
the org's GitHub organization, a manifest resolving from a declared `internal_registries` host, or
an existing self-registered producer in the instance repo) and needs a name pinned manually — most
commonly for ecosystems with no parser yet, or a non-manifest declaration (e.g. a package named in
a generated pipeline job's runtime install parameter, not a standard manifest file).

```go
// panopticon-dependency acme-internal-metrics
require github.com/acme/internal-metrics-lib v1.2.3
```

**Important difference from `panopticon-interface`:** the pinned value (or the raw name, when no
hint is given) is used **exactly as written** — never lowercased or dash-normalized. A dependency's
raw name is already a canonical machine identifier (a Go module path, a Maven
`groupId:artifactId`, a PyPI/npm package name), and normalizing it would break exact matching
against real import paths and registry coordinates (`panopticon/naming.py`'s
`resolve_dependency_name`).

## `panopticon-dependency-of <interface-name>`

**Capability:** dependency-indexing.
**Effect:** declares that the dependency this hint is attached to is the packaged/client form of
an existing **interface** (a REST API, gRPC service, etc.) already tracked by Panopticon — e.g. a
generated REST client SDK for an API another repo owns. The org diagram then renders one edge
covering both the dependency and the interface relationship instead of two separate ones
(architecture-diagrams capability, "Linked dependency and interface edges deduplicate").

```go
// panopticon-dependency-of order-processing-api
require github.com/acme/orders-api-client v1.0.0
```

**Never inferred automatically.** No naming convention (`-api-client-sdk` suffixes,
generator-specific class names, etc.) is trusted to detect this link — codegen conventions vary
too much across orgs and tools, and a wrong guess would silently mislink two unrelated things. Set
this hint only when there's real evidence: the dependency's own docs say what API it wraps, or
you've confirmed it directly.

`<interface-name>` must be the interface's canonical name exactly as it appears in the interface
index (the same name a `panopticon-interface` hint would pin, or the name Panopticon already
resolved without one). If the named interface isn't found in the extracting repo's own local
interface index at extraction time, the link is silently left unset rather than fabricated — the
dependency entry itself is still recorded correctly either way.

## CI behavior when a hint is needed but missing

Every hint form above is a local-judgment mechanism: the local agent (guided by the
panopticon-interface-naming / panopticon-dependency-naming skills) can use LLM judgment to resolve
an ambiguous case and write the hint back. **CI never performs that judgment** — if a PR touches a
candidate interface or dependency that can't be resolved from hints or deterministic rules alone,
the check fails with an explicit instruction naming which hint to add and where
(`panopticon/naming.py`'s `UnresolvableNameError`). This keeps merges reproducible: once the hint
is committed, resolution is deterministic on every future run, locally and in CI alike.
