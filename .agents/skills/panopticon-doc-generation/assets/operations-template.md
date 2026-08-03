# {Repo name} — operations

<!-- panopticon-analysis-scope:start -->
## Panopticon analysis scope

Panopticon excludes illustrative material from interface, dependency, and doc-drift analysis.
The generated section below lists the repository-relative illustrative directories currently
excluded. Exact directory components `examples`, `samples`, `fixtures`, `testdata`, `demos`,
`scaffolding`, `demo`, and `scaffold` are excluded case-insensitively; `src/sample-service` stays
in scope. Use `panopticon-ignore file` in one of a file's first five nonblank lines to exclude the
file, or `panopticon-ignore declaration` on a declaration or the immediately preceding line to
exclude that declaration.

<!-- panopticon-analysis-scope:end -->

## Running locally

{Prerequisites and the exact commands to run the system locally, including any seed/setup steps.}

## Testing

{How to run the test suites, what each suite covers, and pass criteria.}

## Deployment

{How this repo reaches production: pipeline, environments, approvals, rollback. If deployment is
owned elsewhere, link to it.}

## Required configuration

{Everything that must be configured for the system to run: environment variables, secrets (names
only — never values), config files. State where each is provided per environment.}

## Observability

{Where logs, metrics, dashboards, and alerts live, and the first places to look when something is
wrong.}
