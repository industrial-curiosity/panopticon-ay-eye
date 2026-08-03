---
name: panopticon-dependency-extraction
description: >-
  Identify internal (same-org) library/package dependencies in manifest and source files that no
  deterministic Panopticon dependency parser covers, and emit dependency candidates. Apply during
  local dependency indexing for files the parsers skipped — including dependencies declared
  outside a standard manifest (e.g. a generated pipeline job's runtime package-install parameter);
  also loaded as the CI system prompt for diff-scoped LLM extraction fallback.
---

# Panopticon dependency extraction (LLM fallback)

## Analysis scope

Never identify dependencies from an exact illustrative directory component (`examples`, `samples`,
`fixtures`, `testdata`, `demos`, `scaffolding`, `demo`, or `scaffold`, case-insensitive), from a
file carrying `panopticon-ignore file` in its first five nonblank lines, or from a declaration
marked `panopticon-ignore declaration` on that line or immediately before it. The driver filters
those files before invoking this skill and redacts marked declarations from fallback content; do
not reconstruct or return an ignored candidate from surrounding context.

You are given file contents from one repository. Identify every **internal (same-org) library or
package dependency** they declare, publish, or import: package-manager manifests (`go.mod`,
`package.json`, `pyproject.toml`, `build.gradle`, etc.), lockfiles, and any other file that names a
dependency outside a manifest (a CI job parameter, a pipeline step, a generated deployment
config). Ignore third-party (non-org) dependencies entirely — this is not a general dependency
inventory, only the same-org subset.

## Judgment rules

- A dependency is **internal** when there's real evidence it belongs to the same org: a naming or
  URL convention consistent with the org's own repos/registries, a host matching a registry the
  org has declared, or a `panopticon-dependency`/`panopticon-dependency-of` hint. Do not guess
  from a package name alone with no other signal — an ambiguous case is better left unreported
  than reported wrong.
- A file that **declares this repo publishes** the package (a manifest's own `name`/module-path
  field, corroborated by a publish step targeting an internal registry, or a
  `panopticon-dependency` hint) means this repo is a `producer` and `owned` is true.
- A file that **depends on** an internal package means `role: "consumer"` and `owned` false.
- When you can identify specific modules/functions/classes actually imported from the dependency
  (not just that the dependency exists), list their exact paths/names in `apis` — import-level
  granularity, not call-site or symbol-level. Omit `apis` (or use `null`) when you can't determine
  this from the given files.
- Honor `panopticon-dependency <name>` hint comments: copy the hint value into `hint`.
- Honor `panopticon-dependency-of <interface-name>` hint comments: copy the hint value into
  `links_to_interface_hint`. Never infer this link yourself without an explicit hint — a
  dependency that happens to be a generated API client is not automatically "the same thing" as
  an interface unless a hint says so.
- Use `ecosystem` values consistent with the package manager: `go`, `npm`, `python`, `java`,
  `maven`, `gradle` — or the closest lowercase short token for anything else.
- Do not invent dependencies that are not clearly evidenced in the provided files. An empty result
  is a valid result.

## Response contract (strict)

Respond with **only** a JSON array — no prose, no code fences. Each element:

```json
{
  "raw_name": "acme-shared-auth-lib",
  "hint": null,
  "ecosystem": "python",
  "role": "consumer",
  "owned": false,
  "component": null,
  "source_file": "requirements.txt",
  "apis": ["acme_shared_auth.client"],
  "links_to_interface_hint": null
}
```

- `raw_name`: the dependency's name/coordinates exactly as found in the file
- `hint`: value of a `panopticon-dependency` hint covering this declaration, else null
- `role`: `"producer"` or `"consumer"`
- `component`: the owning component when identifiable from the file, else null
- `source_file`: the file's path exactly as given in the section header
- `apis`: list of imported modules/packages, or null when not determinable
- `links_to_interface_hint`: value of a `panopticon-dependency-of` hint covering this declaration,
  else null

Return `[]` when no internal dependencies are present.
