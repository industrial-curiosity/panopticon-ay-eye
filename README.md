# panopticon-ay-eye

<!-- Centered media uses HTML because Markdown cannot align it; a plain image
would lose the README's intentional visual balance. -->
<!-- markdownlint-disable MD033 -->
<p align="center">
  <img src="https://industrialcuriosity.com/images/panopticon/panopticon-logo-chip.png" alt="Panopticon logo" />
</p>
<!-- markdownlint-enable MD033 -->

## [View the organization architecture](docs/architecture.md)

Panopticon gives an organization a shared view of its system architecture:
repository documentation,
runtime interfaces, and internal package dependencies. It helps teams see
cross-repository changes before
they land.

## Start here

Panopticon is a public template for giving an organization one shared view of
its repositories, documentation, interfaces, and internal dependencies.

To get started:

1. Create a private instance from this template.
2. Configure its LLM provider by following the [provider-configuration
   guide](docs/provider-configuration.md).
3. For an organization with centralized credentials or custom access policy,
   generate a reviewed instance overlay with the [complex-organization
   template guide](docs/complex-organization-template.md).
4. Initialize each child repository with the public launcher, run from that
   repository:

```bash
curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | python3
```

For a non-interactive run, set `PANOPTICON_INSTANCE=YOUR-ORG/YOUR-INSTANCE-REPO`,
for example `PANOPTICON_INSTANCE=acme/panopticon-instance`. Authenticate every
install with `GH_TOKEN`, `GITHUB_TOKEN`, or an existing `gh auth` session;
authentication is required for private instances and provides a higher GitHub
API quota. Keep token values in your shell or CI secret environment, never in
the launcher command.

For the complete setup process and operational guidance, see the [org-owner
setup guide](docs/setup-guide.md). After initialization, review the child
repository's `panopticon-initialization-report.md` and follow any actions it
lists.

## Optional instance features

Optional capabilities are selected by the instance maintainer from the
template-owned `features/manifest.json` registry. Open the instance's
[Configure Panopticon — Features workflow](https://github.com/YOUR-ORG/YOUR-INSTANCE-REPO/actions/workflows/configure-panopticon-features.yml)
with `YOUR-ORG` and `YOUR-INSTANCE-REPO` replaced by the real instance
repository, then choose a feature such as `okf` and one of `disabled`,
`advisory`, or `blocking`. The workflow accepts identifiers and modes only; it
does not accept secret values or arbitrary artifact paths.

New children receive only artifacts for enabled features. Bootstrap prompts
before deleting receipt-owned artifacts when a feature is disabled; non-
interactive bootstrap and `python3 -m panopticon.sync` remove those exact
retired paths without staging or committing the deletion. Start OKF in
`advisory` mode for migration: its findings do not block CI, but the installed
feature skill makes deterministic repairs required agent work before
initialization is declared complete. Move to `blocking` when the bundle is
clean.

## How it works

Panopticon has three repository roles:

- **Template** — this public repository provides the shared tooling, workflows,
  and skills.
- **Instance** — one private knowledge-base repository per organization, created
  from the template.
- **Child repository** — an organization repository connected to its instance.

The workflow is intentionally simple:

1. Initialize a child repository to generate its architecture documentation and
   local indexes. During documentation generation, the child compares proposed
   interface names with the instance's existing compiled index and persists
   reviewed naming decisions as source/configuration hints.
2. On pull requests, Panopticon checks behavior-bearing changes against
   documentation, compares likely interface matches with the instance index,
   and predicts interface conflicts. Managed Panopticon metadata and
   documentation-only changes pass without an LLM review; product changes are
   planned and evaluated in isolated documentation batches. LLM-backed reports
   include safe request diagnostics, while tooling-currency drift remains
   advisory with details in the workflow summary.
3. On merge, the instance collects documentation and indexes to build an
   organization-wide view.
4. When planning a change, developers and agents use that shared view to
   understand affected connections.

Panopticon deliberately excludes illustrative directories (`examples`, `samples`, `fixtures`,
`testdata`, `demos`, `scaffolding`, `demo`, and `scaffold`) from analysis while retaining similarly
named production paths such as `src/sample-service`. A child repository's generated
`operations.md` lists the excluded folders actually present and documents the explicit
`panopticon-ignore file` and `panopticon-ignore declaration` escape hatches.

The organization architecture is a complete interface inventory: it includes
interfaces even when only one repository participates, and highlights detected
ownership/type conflicts and potential same-name collisions.

Interface-conflict checks are advisory by default. The instance sets the default
in `panopticon.config.json`, and a child repository may override that check in
its committed `panopticon/config.json` with
`gating.interface-conflict: "advisory"` or `"blocking"`. Both modes publish a
prominent warning; only `blocking` fails the PR check.

Child repositories can also run the manual **Panopticon resource sync** workflow
to refresh their managed skills and local tooling. It opens or updates a
reviewable open pull request instead of changing the default branch directly.
After that pull request is merged or closed, the next changed sync creates a
new pull request.

Run `python3 -m panopticon.sync` in an initialized child repository to refresh
managed skills, local tooling, and Panopticon workflow callers. Use
`python3 -m panopticon.sync --check-updates` to preview the resulting changes.
Each run downloads the versioned, data-only child-safe tooling manifest from
the selected instance branch, so a child repository's vendored manifest cannot
expand the set of files sync manages. It warns, without deleting them, about
Python modules outside the manifest so maintainers can review legacy or
child-owned files.

Child-local documentation links stay relative to the document that contains
them. Generated links from a child README or architecture overview to the
organization architecture use the resolver-produced direct GitHub URL, so they
work from both the child and instance repositories.

## Documentation

- [Set up an organization instance](docs/setup-guide.md)
- [Configure provider defaults](docs/provider-configuration.md)
- [Generate a complex-organization instance overlay](docs/complex-organization-template.md)
- [Contribution guidelines](CONTRIBUTING.md)
- [Contribute a parser](docs/parser-contribution.md)
- [Use interface and dependency hints](docs/hint-reference.md)
- [Run the test suite](docs/testing.md)
- [View the organization architecture](docs/architecture.md)

## Repository contents

- `panopticon/` — Python tooling used by the template, instance, and CI
  workflows.
- `.github/workflows/` — shared automation for configuration, evaluation, merge,
  and template sync.
- `interfaces/` and `dependencies/` — organization-wide indexes populated in an
  instance.
- `docs/` — setup, contribution, and reference documentation.
- `features/` — the versioned registry and template-owned optional feature packages.
- `.agents/skills/` — skills used by local agents and CI.

For configuration details, supported providers, sync protection rules, and
operational procedures, use the
[org-owner setup guide](docs/setup-guide.md) rather than relying on this
overview.

<!-- Centered media uses HTML because Markdown cannot align it; a plain linked
thumbnail would lose the README's intentional visual balance. -->
<!-- markdownlint-disable MD033 -->
<p align="center">
  <a href="https://www.youtube.com/watch?v=sIJ9XhBSkI8" target="_blank" rel="noopener noreferrer">
    <img src="https://img.youtube.com/vi/sIJ9XhBSkI8/hqdefault.jpg" alt="Watch the Panopticon introduction on YouTube" />
  </a>
</p>
<!-- markdownlint-enable MD033 -->
