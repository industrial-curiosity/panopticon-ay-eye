# Panopticon technical workflow architecture

## Purpose

This document summarizes the stable technical boundaries between Panopticon's template, instance, and child
repositories. Operational setup belongs in the [org-owner setup guide](setup-guide.md).

## Repository roles

- The public template owns deterministic Python tooling, trusted workflow and action implementations, and
  agent skills.
- Each organization creates a private instance that owns organization configuration, generated
  documentation, index shards, and compiled indexes.
- Child repositories own their local documentation and indexes and invoke the instance's reusable
  evaluation and synchronization workflows.

## Provider configuration

An instance starts without an implicit LLM provider. Its maintainer runs exactly one fixed-provider manual
workflow:

- `.github/workflows/configure-panopticon-litellm.yml`
- `.github/workflows/configure-panopticon-bedrock.yml`

Each workflow exposes only GitHub Actions secret and variable *names*, never credential values. Both check
out the instance and invoke `.github/actions/configure-panopticon/action.yml`, which uses the trusted provider
registry and deterministic `panopticon.configure_instance` module to validate and persist
`panopticon.config.json`. The callers share a branch-scoped concurrency group so only one configuration
mutation runs at a time.

Provider configuration selects trusted reusable PR workflow paths and canonical input mappings; it cannot
inject an arbitrary repository, workflow, action, or command. Splitting the manual entrypoints does not
change the persisted provider schema, effective contract revision, or generated child caller.

## Evaluation and synchronization

Child PR callers invoke the selected LiteLLM or Bedrock evaluation workflow with explicit organization-level
secret and variable mappings. Provider-neutral checks share prompting, validation, correction, reporting,
and gating behavior; authentication and transport remain inside the provider entrypoint.

On child merge, deterministic synchronization copies generated documentation, replaces that repository's
index shard, and rebuilds compiled indexes in the instance. Pull requests simulate the same merge behavior
and publish in-flight branch state without changing the instance's default branch.
