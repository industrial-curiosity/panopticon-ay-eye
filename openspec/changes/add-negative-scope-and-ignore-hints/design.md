# Deterministic analysis scope design

## Context

All deterministic interface parsers and both LLM fallback selectors currently traverse the
shared parser iterator. That iterator excludes generated and dependency directories, but it
does not recognize illustrative material. Doc drift independently classifies changed paths and
passes its complete eligible diff to the LLM. The existing hint grammar handles valued naming
hints only and has no exclusion semantics.

The change must keep structural scope decisions deterministic, prevent excluded material from
reaching an LLM, retain real production paths with similar names, and make exclusions visible in
both workflow output and repository documentation.

## Goals / Non-Goals

**Goals:**

- Apply one deterministic scope decision to interface extraction, dependency extraction,
  component-documentation input, and doc-drift preparation.
- Support explicit whole-file and declaration-level exclusions in comment-capable source or
  configuration files.
- Report each exclusion with a stable reason and document the repository's path-based exclusions.
- Preserve the existing four documentation layers and their ownership boundaries.

**Non-Goals:**

- Infer whether arbitrary test code is illustrative from its contents.
- Add configuration for organization-specific ignore lists.
- Suppress a source file merely because a filename contains an illustrative word.
- Change the interface or dependency index schema, gating modes, or LLM naming behavior.

## Decisions

### One stdlib-only scope module owns classification

`panopticon.scope` will expose deterministic path, file, and declaration decisions. The
existing parser iterator will use it before returning files; extraction drivers and doc drift will
use the same module rather than reproduce path lists. This preserves the template's
deterministic-first architecture and makes new parsers inherit the policy automatically.

The default path policy matches an exact directory component, not a substring, against
`examples`, `samples`, `fixtures`, `testdata`, `demos`, `scaffolding`, `demo`, and `scaffold`.
For example, `examples/openapi.yaml` is excluded while
`src/sample-service/openapi.yaml` remains in scope. Matching ignores directory-name case but
does not match a longer component such as `examples-api`.

The policy applies identically to dependency evidence. An internal dependency declaration or
import under an illustrative directory is excluded before deterministic parsing or LLM fallback;
the dependency index must not retain it merely because its package identity is internal.

### Hints use explicit modes and fixed placement

The new valued forms are `panopticon-ignore file` and
`panopticon-ignore declaration`. A file hint is valid only in the first five nonblank lines;
a declaration hint is valid only on the declaration's line or the immediately preceding line.
They are source annotations, never index/configuration fields. The explicit mode avoids a bare
comment with ambiguous file versus declaration meaning and fits the established hint reference.

Built-in text parsers will attach source line information to candidates. The central extraction
drivers will remove candidates marked by a declaration hint. For LLM fallback, the scope module
will omit file-scoped files and redact a declaration hint together with its annotated line before
assembling prompt content. Comment-free formats cannot express a declaration hint; path scope
continues to apply to them.

### Scope decisions are first-class diagnostics

Every consumer will emit stable summary entries identifying the repository-relative path or
declaration location and one of: illustrative directory, explicit file hint, or explicit
declaration hint. A clean no-candidate result is not silent when scope exclusions occurred.

Doc drift will remove excluded files and ignored declaration text from the material provided to
the LLM. If no behavior-bearing material remains after this preparation, it returns its existing
clean verdict without an LLM request.

### Operations documentation carries a managed scope section

`operations.md` remains the detailed repo-wide operational document. A managed
`## Panopticon analysis scope` section, delimited by stable generated markers, will list every
illustrative directory actually found and excluded in the repository, plus the default directory
set and hint syntax. Deterministic documentation tooling updates this section in place and
validation requires it. The operations template gains the section so first-time generation has
the required anchor.

The architecture template keeps the org-diagram link and adds a plain relative
`operations.md#panopticon-analysis-scope` link directly below the diagram. This gives readers an
immediate route from the detailed architecture to the analysis boundary without adding a fifth
documentation layer.

## Risks / Trade-offs

- [A real repository deliberately uses an illustrative directory name] → Exact component matching,
  visible reports, and the small fixed list make the exclusion reviewable; moving production
  material outside that illustrative path restores normal analysis.
- [A parser fails to preserve declaration line information] → Update every shipped text parser and
  test the common candidate filter; parser contribution guidance will require line metadata for
  declaration-level support.
- [A prompt includes multiline material belonging to an ignored declaration] → The first release
  redacts the annotated line and requires parser-specific candidates to carry the declaration
  line; unsupported multiline declaration formats remain file-scope-only until their parser can
  define a safe span.
- [Managed documentation conflicts with agent-authored operations prose] → Markers limit
  deterministic rewriting to the scope section and leave every other section untouched.

## Migration Plan

1. Ship the module, integrations, templates, skills, and specifications together in the template.
2. Child repositories receive the new module through the local-tooling manifest on bootstrap or
   sync.
3. Regenerate child documentation to add or refresh the managed scope section and architecture
   link; validation names the missing section and the render command when a repository is stale.
4. No index migration is needed because ignored candidates are simply absent from subsequently
   regenerated local indexes.

## Open Questions

None.
