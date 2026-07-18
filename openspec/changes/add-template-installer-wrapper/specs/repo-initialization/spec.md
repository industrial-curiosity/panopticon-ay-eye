# Repository Initialization Delta

## MODIFIED Requirements

### Requirement: Bootstrap installer script

The template repo SHALL publish a Python standard-library-only launcher that can be piped directly into
Python from a stable, organization-neutral public-template URL while the user's working directory is the
child repo to initialize. The same launcher command SHALL support public and private instance repositories.

The launcher SHALL resolve the instance org/repo slug from `PANOPTICON_INSTANCE`, or prompt through the
controlling terminal when the variable is absent and interactive input is available. It SHALL resolve the
instance ref from `PANOPTICON_INSTANCE_REF` when set; otherwise it SHALL query the GitHub repository API
for the instance repository's actual default branch rather than assuming a branch name.

Authentication SHALL be resolved in this order: `GH_TOKEN`, `GITHUB_TOKEN`, then `gh auth token` when the
GitHub CLI is available. With no resolved token, the launcher SHALL first attempt anonymous GitHub API
access so public instances require no authentication. When anonymous access cannot retrieve the instance
and a controlling terminal is available, the launcher SHALL offer a hidden token prompt and retry with
the entered token. In non-interactive execution it SHALL fail clearly and name the environment variables
needed to continue.

After resolving access and the ref, the launcher SHALL fetch the selected instance repository's complete
`install.py` through the GitHub contents API and execute it as the installation payload in the current
process and child-repository working directory. It SHALL pass through the existing environment unchanged,
apart from making launcher-resolved universal values available to the payload, so the instance installer
retains control of organization-specific prompts, parameters, skills locations, files, and behavior. The
launcher SHALL prevent a fetched payload from recursively re-entering the launcher dispatch phase.

The launcher and its diagnostics SHALL never place a token in a URL or command argument, echo a token,
include a token or authenticated response body in an error, or persist a prompted token to disk or Git
credential storage. Hidden token input SHALL not be displayed. A token entered interactively SHALL exist
only for the lifetime of the launcher process and its instance-installer payload.

The instance installer remains responsible for the deterministic installation behavior defined by the
instance, including the template default behavior of selecting a skills location, downloading only
`panopticon-` skills, vendoring local tooling and the getting-started guide, writing caller workflows,
refreshing an existing `panopticon/config.json`, reporting CI prerequisites, and printing agent and sync
instructions. The instance installer SHALL NOT create `panopticon/config.json`; finalization remains
responsible for its initial creation after validation.

#### Scenario: Public instance uses anonymous access

- **GIVEN** `PANOPTICON_INSTANCE` names a public instance repository and no GitHub token is available
- **WHEN** the user pipes the public template launcher into Python
- **THEN** the launcher resolves the default branch, retrieves the instance `install.py` anonymously,
  and executes it without asking for authentication

#### Scenario: Private instance uses existing authentication

- **GIVEN** `PANOPTICON_INSTANCE` names a private instance repository and `GH_TOKEN`, `GITHUB_TOKEN`, or
  `gh auth token` provides access
- **WHEN** the public template launcher runs
- **THEN** the launcher retrieves and executes the private instance's `install.py` without exposing the
  token

#### Scenario: Private instance prompts securely for authentication

- **GIVEN** the instance installer cannot be retrieved anonymously, no existing token is available, and
  the launcher has a controlling terminal
- **WHEN** the public template launcher runs
- **THEN** it requests a token using hidden input, retries the GitHub API request, and makes the token
  available to the instance payload only for the current process without displaying or persisting it

#### Scenario: Missing instance is prompted while launcher input is piped

- **GIVEN** `PANOPTICON_INSTANCE` is unset and the launcher source is arriving through piped stdin
- **WHEN** a controlling terminal is available
- **THEN** the launcher prompts for `owner/repo` through the controlling terminal and continues without
  consuming installer-source bytes as user input

#### Scenario: Non-interactive inputs are incomplete

- **GIVEN** no controlling terminal is available
- **WHEN** the instance slug or authentication required to retrieve a private instance is unavailable
- **THEN** the launcher exits non-zero with instructions naming `PANOPTICON_INSTANCE` and the applicable
  token environment variables, without printing secret values

#### Scenario: Explicit instance ref is honored

- **GIVEN** `PANOPTICON_INSTANCE_REF` names a branch, tag, or commit containing a customized installer
- **WHEN** the launcher retrieves the instance payload
- **THEN** it fetches `install.py` at that exact ref instead of resolving or using the default branch

#### Scenario: Customized instance installer receives control

- **GIVEN** the selected instance's `install.py` defines organization-specific prompts and installation
  behavior
- **WHEN** the launcher executes the fetched payload
- **THEN** the payload runs in the child repository with terminal access and the caller's environment,
  including `PANOPTICON_SKILLS_LOCATION` when supplied, without the launcher imposing template bootstrap
  steps

#### Scenario: Instance payload does not recursively dispatch

- **GIVEN** the fetched instance installer was forked from a template version that recognizes the
  launcher execution marker
- **WHEN** it starts as the selected payload
- **THEN** it performs instance installation rather than fetching and executing itself again

#### Scenario: Default template instance behavior remains available

- **GIVEN** an instance has not customized the template's installation payload
- **WHEN** its fetched `install.py` executes
- **THEN** it installs the instance's Panopticon skills, tooling, workflows, and guide, prints the agent
  prompt, and does not create `panopticon/config.json`

#### Scenario: Re-run remains idempotent

- **WHEN** the public launcher dispatches the instance installer in an already-bootstrapped child repo
- **THEN** the instance installer updates its managed files in place and does not duplicate them
