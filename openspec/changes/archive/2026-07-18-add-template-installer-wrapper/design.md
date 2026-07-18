# Public Template Installer Wrapper Design

## Context

Today the documented command retrieves `install.py` from the instance repository. That works directly
for a public instance, but a private instance requires the user to authenticate before any installer code
can run. The current template entry point also embeds self-bootstrap assumptions about the instance's
Python modules, even though an organization may heavily customize its complete installer.

The public template is the stable delivery point. The private instance remains the authority for
organization-specific installation. The launcher must therefore solve only the universal bootstrapping
problem: identify the instance, obtain access, select its ref, and transfer control safely.

## Goals / Non-Goals

**Goals:**

- Provide one short public command for both public and private instances.
- Prompt for missing universal values even when Python source arrives through a pipe.
- Preserve non-interactive operation through environment variables.
- Execute the complete instance-owned installer without constraining its customization surface.
- Keep all authentication material out of visible commands, output, errors, and persistent storage.
- Remain Python standard-library only.

**Non-Goals:**

- Standardize organization-specific installer parameters or steps.
- Move skills-location selection or child-repo initialization into the public launcher.
- Persist credentials or configure GitHub CLI authentication.
- Replace the existing instance bootstrap implementation; an uncustomized instance can continue using it
  as its payload.
- Guarantee compatibility with arbitrary historical instance installers that predate the launcher/payload
  boundary.

## Decisions

### The template `install.py` becomes a launcher

The public file resolves only `PANOPTICON_INSTANCE`, optional `PANOPTICON_INSTANCE_REF`, and GitHub
authentication. It then downloads the instance's entire `install.py`. This keeps the public contract
small and ensures instance forks can replace any downstream installation behavior.

Fetching template bootstrap modules directly was rejected because it silently bypasses custom logic in
the instance's entry point. Maintaining separate public and private user commands was rejected because it
preserves the authentication chicken-and-egg problem and increases documentation drift.

### Terminal prompts use the controlling terminal

The launcher reads interactive values from `/dev/tty` when available rather than stdin. Piped stdin is
occupied by the launcher source, so ordinary `input()` cannot reliably gather values. On platforms or
executions without a controlling terminal, the launcher fails with environment-variable instructions.

The instance slug uses visible input. A token prompt uses `getpass` bound to the controlling terminal so
the secret is not echoed. The launcher first tries anonymous access, avoiding an unnecessary credential
prompt for public repositories.

### GitHub API access is implemented in Python

The launcher uses `urllib.request` with an authorization header when a token is available. It discovers
tokens from `GH_TOKEN`, `GITHUB_TOKEN`, and `gh auth token`, in that order. Tokens never appear in request
URLs or subprocess arguments. GitHub CLI is only a token source; `gh api` is not the transport.

Raw authenticated error bodies are not printed. Diagnostics report the repository, requested ref or
operation, and HTTP status using controlled text. This prevents a customized endpoint or unexpected
response from reflecting sensitive input into logs.

The GitHub contents API may line-wrap its base64 `content` field. Both the public launcher and the
template-derived payload remove transport whitespace before applying strict base64 and UTF-8 validation.
This accepts the API's representation without weakening rejection of malformed executable content.

### Default branch resolution precedes payload retrieval

When `PANOPTICON_INSTANCE_REF` is absent, the launcher queries repository metadata and uses
`default_branch`. This avoids hardcoding `main` and supports customized forks whose default branch differs.
An explicit ref is useful for testing or pinned automation and bypasses default-branch discovery.

### The payload executes in-process with an explicit boundary marker

The launcher compiles the fetched bytes with an instance-specific filename and executes them with
`__name__ == "__main__"`, preserving the child repository's working directory and controlling-terminal
access. Universal values resolved by prompts are added to the process environment for the payload.

An internal launcher marker distinguishes dispatch from payload execution. The template's instance-side
entry behavior checks that marker and runs the normal instance bootstrap instead of dispatching again.
The marker is an implementation detail, not a user configuration surface.

A subprocess or temporary installer file was rejected because both create avoidable secret-propagation
or cleanup concerns. In-process execution also matches the existing self-bootstrap trust model: the user
has selected and authorized execution of code from the instance repository.

### The instance installer owns all remaining prompts

The launcher passes through arbitrary environment variables, including `PANOPTICON_SKILLS_LOCATION`, but
does not interpret them. This lets an uncustomized instance retain the current skills menu while allowing
custom instances to add, remove, or replace parameters and installation steps.

## Risks / Trade-offs

- **A compromised instance installer executes arbitrary code** → This is inherent to installing from the
  selected instance; display the resolved repository and ref before executing and fetch only through the
  GitHub API over HTTPS.
- **An unauthenticated 404 is ambiguous between a private repository and a typo** → In interactive mode,
  offer one hidden authentication retry; after authenticated failure, report a controlled repository/ref
  error. In non-interactive mode, explain both the access and identifier possibilities.
- **Historical customized installers may recursively dispatch** → Define and document the internal marker,
  test the template-derived payload path, and state the minimum compatible launcher contract for custom
  instances.
- **Adding a prompted token to the process environment exposes it to trusted payload code** → The payload
  requires that token for subsequent private-instance downloads; scope it to the current process and never
  write it to disk or external credential stores.
- **In-process `exec` shares launcher globals and interpreter state** → Execute in a fresh globals mapping
  containing only normal script metadata and the boundary marker contract.

## Migration Plan

1. Add launcher-focused unit and subprocess tests, including controlling-terminal, secret-redaction, and
   GitHub-style line-wrapped base64 cases.
2. Convert the template `install.py` into the launcher/payload entry point while retaining the existing
   uncustomized instance bootstrap path behind the boundary marker.
3. Update public documentation to publish the single template URL and list optional environment variables.
4. Validate an uncustomized public instance, an authenticated private instance, and non-interactive
   failures with stubbed GitHub API responses.
5. Existing instance forks receive the launcher-compatible entry point when they intentionally sync or
   merge this template change; their customized payload logic remains instance-owned.

Rollback consists of restoring the previous template `install.py` and its prior instance-specific
documentation. No child-repository data migration is required because the launcher changes delivery, not
the installed data model.

## Open Questions

None. The environment contract, authentication precedence, ref behavior, and launcher/payload ownership
boundary are defined by this change.
