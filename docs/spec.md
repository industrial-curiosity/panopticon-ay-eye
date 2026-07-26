# Panopticon technical workflow architecture

## Purpose

This document summarizes the stable technical boundaries between Panopticon's
template, instance, and child
repositories. Operational setup belongs in the [org-owner setup
guide](setup-guide.md).

Child-repository finalization writes `panopticon-initialization-report.md` on
every attempt before it creates the `panopticon/config.json` initialization flag.
The report separates child-repository, organization-configuration, and
template/tooling findings and gives the next action for each; credential values
are never recorded.

Initialization is one continuous sequence: before finalization writes the
configuration file, documentation generation derives its repository, instance,
and workflow-reference context from the bootstrap caller workflow. GitHub API
clients retry transient failures and recognized rate limits using the full
GitHub-provided `Retry-After` or reset timing when available; they do not retry
while GitHub still directs them to wait. Users should authenticate every install,
including public-instance installs, to avoid the lower anonymous API quota;
tokens are also required for private instances.

## Repository roles

- The public template owns deterministic Python tooling, trusted workflow and
  action implementations, and
  agent skills. Its root-level [`CONTRIBUTING.md`](../CONTRIBUTING.md) documents
  the OpenSpec-based
  contributor workflow for changes to those assets.
- Each organization creates a private instance that owns organization
  configuration, generated
  documentation, index shards, and compiled indexes.
- Child repositories own their local documentation and indexes and invoke the
  instance's reusable
  evaluation and synchronization workflows.

## Provider configuration

An instance starts without an implicit LLM provider. Its maintainer runs exactly
one fixed-provider manual
workflow:

- `.github/workflows/configure-panopticon-litellm.yml`
- `.github/workflows/configure-panopticon-openai.yml`
- `.github/workflows/configure-panopticon-bedrock.yml`

Each workflow exposes only GitHub Actions secret and variable *names*, never
credential values. Both check
out the instance and invoke `.github/actions/configure-panopticon/action.yml`,
which uses the trusted provider
registry and deterministic `panopticon.configure_instance` module to validate
and persist
`panopticon.config.json`. The callers share a branch-scoped concurrency group so
only one configuration
mutation runs at a time.

The OpenAI workflow fixes its base URL to `https://api.openai.com/v1`; it does
not expose, persist, or forward an endpoint variable. LiteLLM remains the
provider for a configurable OpenAI-compatible endpoint.

Provider configuration selects trusted reusable PR workflow paths and canonical
input mappings; it cannot
inject an arbitrary repository, workflow, action, or command. Splitting the
manual entrypoints does not
change the persisted provider schema, effective contract revision, or generated
child caller.

## Evaluation and synchronization

Child PR callers invoke the selected LiteLLM, OpenAI, or Bedrock evaluation workflow with
explicit organization-level
secret and variable mappings. Provider-neutral checks share prompting,
validation, correction, reporting,
and gating behavior; authentication and transport remain inside the provider
entrypoint.

Bootstrap also wires a stable, manual child resource-sync caller to a
template-owned reusable workflow. It refreshes only managed Panopticon skills
and vendored tooling, uses the instance token only for that read, and opens or
updates a child-repository pull request for review when resources changed.

The documentation-drift check first classifies the PR diff. Documentation,
agent guidance and templates, OpenSpec artifacts, changelogs, and test-only
changes are clean without an LLM request. For behavior-bearing changes, every
stale-doc finding must name the changed behavior file that supports it and a
specific required documentation update. Invalid, contradictory, or unsupported
findings are operational failures, not stale-doc verdicts.

On child merge, deterministic synchronization copies generated documentation,
replaces that repository's
index shard, and rebuilds compiled indexes in the instance. Pull requests
simulate the same merge behavior
and publish in-flight branch state without changing the instance's default
branch. Instance template syncs preserve declared instance-owned paths and
report the failing stage and recovery action when they cannot complete.

## Architecture diagram links

Child-local documentation links use paths relative to the document that
contains them, so they work both in the child repository and in its
`docs/{repo}/` instance mirror. Every generated child-to-org architecture link,
including links in the README and architecture overview, uses the resolved
absolute GitHub URL with the child repository anchor. The instance org diagram
continues to use `{repo}/architecture.md` relative links to its mirrored child
documentation.

The organization architecture inventories every participating repository
interface, including interfaces used by one repository alone. Dependencies stay
limited to external relationships. When the compiled index detects an
ownership/type dispute or a potential same-name collision, `## Detected
interface conflicts` summarizes it and highlights the affected Mermaid
resources and table rows.
