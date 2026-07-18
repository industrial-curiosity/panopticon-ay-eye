# Public Template Installer Wrapper Tasks

## 1. Launcher Input and Authentication

- [x] 1.1 Refactor `install.py` into explicit launcher and instance-payload paths protected by a non-recursive internal execution marker
- [x] 1.2 Implement controlling-terminal input for a missing `PANOPTICON_INSTANCE` and hidden token input that also works when source arrives through piped stdin
- [x] 1.3 Implement token precedence across `GH_TOKEN`, `GITHUB_TOKEN`, and `gh auth token`, followed by anonymous access and an interactive authentication retry
- [x] 1.4 Implement `PANOPTICON_INSTANCE_REF` support and GitHub API default-branch resolution without assuming `main`

## 2. Secure Payload Dispatch

- [x] 2.1 Fetch the instance repository's complete `install.py` through the GitHub contents API using headers rather than credential-bearing URLs or command arguments
- [x] 2.2 Add controlled error handling that reports actionable repository, ref, authentication, and non-interactive failures without printing tokens or raw authenticated response bodies
- [x] 2.3 Execute the fetched instance installer in-process from the child-repository working directory with terminal access and pass-through environment variables
- [x] 2.4 Preserve the existing template bootstrap as the default instance payload behavior while allowing customized instance installers to replace its prompts and steps

## 3. Verification

- [x] 3.1 Extend self-bootstrap tests for public anonymous instances, both token environment variables, GitHub CLI token fallback, explicit refs, and resolved default branches
- [x] 3.2 Add pseudo-terminal tests for piped-source instance prompts and hidden authentication prompts, including assertions that secrets never appear in stdout or stderr
- [x] 3.3 Add subprocess and isolated-process tests for non-interactive failures, invalid repositories or refs, authenticated retry failures, and recursion prevention
- [x] 3.4 Verify the uncustomized instance payload retains idempotent skills, tooling, workflow, guide, config-refresh, and prompt behavior
- [x] 3.5 Run the complete test suite and strict OpenSpec validation

## 4. Documentation

- [x] 4.1 Update the setup guide and installer usage text to publish one organization-neutral public-template command and document optional automation environment variables
- [x] 4.2 Update README.md and the repository-initialization OpenSpec to reflect the user-facing and architectural changes; `docs/spec.md` does not exist in this project
