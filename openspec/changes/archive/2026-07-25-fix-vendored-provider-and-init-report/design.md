# Design: vendored provider tooling and initialization reports

## Context

Bootstrap and `panopticon.sync` each maintain a closed list of local modules
that are copied from an instance into a child repository. The list contains
`config.py`, which imports `providers.py`, but does not contain that dependency.
The child therefore fails before documentation generation or finalization can
offer useful diagnostics.

Finalization already returns structured status and message strings, but the CLI
only prints them. Users lose the result after the terminal session, and the
current wording does not distinguish an application artifact gap from an
organization-level configuration item.

## Goals / Non-Goals

**Goals:**

- Keep the bootstrap and sync module lists identical and runnable without an
  instance clone.
- Write `panopticon-initialization-report.md` in the child root on every
  finalization attempt, before returning success or failure.
- Make the report short, safe to commit or share, and organized by the party
  that can resolve each item.

**Non-Goals:**

- Repair child application code or documentation automatically.
- Treat unavailable organization-secret inspection as proof that configuration
  is missing.
- Change finalization's config-write gate or expose tokens and secret values.

## Decisions

### Share the complete local import closure

Add `providers.py` to both mirrored `LOCAL_TOOLING_MODULES` tuples and retain
the equality regression test. This is the smallest deterministic correction:
the provider registry is a stdlib-only local dependency of `config.py` and is
needed by the commands already promised to child users. Deriving the list at
runtime was rejected because the child must not need the full template package
or an import environment merely to install its tools.

### Use a stable Markdown report in the child root

`init_repo.initialize()` will assemble report data while it validates, then
write `panopticon-initialization-report.md` regardless of outcome. The CLI will
print the report path and a concise outcome, while the file holds the full
actionable record. A command-line-only summary was rejected because it cannot
be reviewed after a failed first-time initialization.

### Classify issues by ownership and recovery action

The report will lead with either a successful-completion statement or a short
blocked summary. Each finding will identify one of `Child repository`,
`Organization configuration`, or `Template/tooling`; state what and where the
problem is; and give the next command or configuration location. Verification
that cannot run will be recorded as `Organization configuration — verification
needed`, not a missing-secret assertion. This preserves the existing
report-only policy for organization prerequisites.

## Risks / Trade-offs

- [A report could go stale after a user repairs files] → Each finalization run
  overwrites it and states the run outcome; guidance tells users to rerun the
  command after remediation.
- [Detailed diagnostics could reveal credentials] → Render configuration names
  and paths only; never render tokens, secret values, or environment values.
- [Mirrored lists can drift again] → Keep and extend the existing equality and
  vendored-file tests.

## Migration Plan

1. Release the template update with the expanded vendored module set.
2. Existing child repositories run `python3 -m panopticon.sync` to fetch
   `providers.py` and the reporting update.
3. Users rerun `python3 -m panopticon.init_repo --instance <owner/name>` to
   create or refresh the report; no config migration is required.

## Open Questions

None.
