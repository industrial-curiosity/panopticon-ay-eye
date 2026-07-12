## Context

`panopticon/diagrams.py` renders `docs/architecture.md` (`ORG_DIAGRAM_PATH = Path("docs") / "architecture.md"`)
deterministically from the compiled interface index. Two places in that module build a markdown
link from the org diagram to a child repo's own diagram, both currently using the href
`docs/{repo}/architecture.md`:

- `render_org_diagram()`'s per-repo section: `f"See this repo's own diagram: [docs/{repo}/architecture.md](docs/{repo}/architecture.md)"`
- `_table()`'s per-row "Other repo" column: `f"[{other}](docs/{other}/architecture.md)"`

Since the org diagram file itself lives inside `docs/`, GitHub resolves that href relative to
`docs/`, landing on `docs/docs/{repo}/architecture.md` — which doesn't exist. Confirmed live on
`industrial-curiosity/panopticon-test/blob/main/docs/architecture.md`: both link forms 404. The
correctly-generated *reverse* link (each child repo's own `architecture.md` back to the org
diagram, `../architecture.md`, generated elsewhere and unaffected by this change) shows the
relative-linking convention this code should have followed.

## Goals / Non-Goals

**Goals:**
- Make both org-diagram-to-child-repo links resolve correctly on GitHub and when checked out locally.
- Make the regression untestable-for-free: strengthen the existing test so the old (buggy) href
  form fails it, not just the presence of some href.
- Remove the ambiguity in the spec wording that reads as an instruction for the literal href text
  when it's actually describing the resolved target path.

**Non-Goals:**
- Not touching `org_diagram_link.py` or the child-repo-side back-link (`../architecture.md`) —
  both are already correct.
- Not adding a migration script to patch already-generated `docs/architecture.md` files in
  existing instance repos; the file is fully regenerated on every merge to a child repo's default
  branch (master-sync capability), so the next sync naturally fixes it.

## Decisions

- **Fix at the href-construction site, not by moving `ORG_DIAGRAM_PATH`.** The org diagram's
  location at `docs/architecture.md` (one level under the instance repo root, alongside every
  child repo's `docs/{repo}/` copy) is an intentional, spec'd layout choice (`master-sync`
  capability) — relocating it to the repo root to make `docs/{repo}/architecture.md` a valid
  relative href would be a much larger, unrelated change. The two f-strings just need to drop the
  redundant `docs/` prefix: `{repo}/architecture.md`.
- **Strengthen the test with the literal correct string, not a resolution simulator.** Building an
  actual relative-path resolver in the test would be disproportionate for a two-line fix; asserting
  the exact literal href (`svc-a/architecture.md` present, `docs/svc-a/architecture.md` absent) is
  enough to pin the fix and catch a regression back to the old form.
- **Edit the spec's existing scenario in place rather than adding a new one.** The current scenario
  text ("leads to `docs/{repo}/architecture.md` in the instance repo") is the exact ambiguity that
  produced the bug — describing the resolved path without saying so, so it read as href text. It
  needs correcting, not supplementing.

## Risks / Trade-offs

- **Existing instance repos stay broken until their next sync.** [Risk] → Mitigation: this is
  inherent to the "regenerated on every merge" design (no incremental patching), already
  established for `docs/architecture.md`; the org's next child-repo merge to its default branch
  regenerates the file correctly. No action needed in this change.
