# panopticon-ay-eye

<p align="center">
  <img src="https://industrialcuriosity.com/images/panopticon/panopticon-logo-chip.png" alt="Panopticon logo" />
</p>

**[View the organization architecture](docs/architecture.md)**

Panopticon gives an organization a shared view of its system architecture: repository documentation,
runtime interfaces, and internal package dependencies. It helps teams see cross-repository changes before
they land.

## Start here

Create a private instance from this template, configure its LLM provider, and initialize child repositories.
The [org-owner setup guide](docs/setup-guide.md) walks through that process, including credentials,
provider choices, template sync, and customization protection.

To initialize a child repository, run the public launcher from that repository:

```bash
curl -fsSL https://raw.githubusercontent.com/industrial-curiosity/panopticon-ay-eye/main/install.py | python3
```

Set `PANOPTICON_INSTANCE=YOUR-ORG/YOUR-INSTANCE-REPO` for a non-interactive run; for example,
`PANOPTICON_INSTANCE=acme/panopticon-instance`. Private instances require `GH_TOKEN`, `GITHUB_TOKEN`, or
an existing `gh auth` session.

## How it works

Panopticon has three repository roles:

- **Template** — this public repository provides the shared tooling, workflows, and skills.
- **Instance** — one private knowledge-base repository per organization, created from the template.
- **Child repository** — an organization repository connected to its instance.

The workflow is intentionally simple:

1. Initialize a child repository to generate its architecture documentation and local indexes.
2. On pull requests, Panopticon checks documentation and predicts interface conflicts.
3. On merge, the instance collects documentation and indexes to build an organization-wide view.
4. When planning a change, developers and agents use that shared view to understand affected connections.

## Documentation

- [Set up an organization instance](docs/setup-guide.md)
- [Contribute a parser](docs/parser-contribution.md)
- [Use interface and dependency hints](docs/hint-reference.md)
- [Run the test suite](docs/testing.md)
- [View the organization architecture](docs/architecture.md)

## Repository contents

- `panopticon/` — Python tooling used by the template, instance, and CI workflows.
- `.github/workflows/` — shared automation for configuration, evaluation, merge, and template sync.
- `interfaces/` and `dependencies/` — organization-wide indexes populated in an instance.
- `docs/` — setup, contribution, and reference documentation.
- `.agents/skills/` — skills used by local agents and CI.

For configuration details, supported providers, sync protection rules, and operational procedures, use the
[org-owner setup guide](docs/setup-guide.md) rather than relying on this overview.

[![Watch the Panopticon introduction on YouTube](https://img.youtube.com/vi/sIJ9XhBSkI8/hqdefault.jpg)](https://www.youtube.com/watch?v=sIJ9XhBSkI8)
