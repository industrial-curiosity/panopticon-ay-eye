# Public Template Installer Wrapper

## Why

The current installation entry point assumes the installer itself comes from the selected instance repository, forcing public and private instances to use different retrieval instructions and requiring authentication before the installer can help. A stable public launcher can gather universal inputs and authentication first, while preserving each instance repository's freedom to provide a heavily customized installer.

## What Changes

- Replace the template's current self-bootstrap behavior with a public launcher that resolves the instance repository, authentication, and instance ref before fetching its installer.
- Prompt through the controlling terminal for missing interactive inputs even when the launcher is piped through `curl`.
- Support public instances anonymously and private instances through `GH_TOKEN`, `GITHUB_TOKEN`, an existing GitHub CLI session, or a hidden token prompt.
- Execute the fetched instance `install.py` from the child repository without constraining its organization-specific parameters or installation behavior.
- Define safe non-interactive behavior and ensure secrets never appear in commands, URLs, logs, diagnostics, or persisted files.
- Update installation documentation to use one organization-neutral public-template command for both public and private instance repositories.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repo-initialization`: Change the bootstrap entry point into a public template launcher that securely dispatches to the selected instance repository's installer.

## Impact

- Affects `install.py`, its installer-loading tests, and the documented bootstrap command.
- Changes the initial download flow while leaving the instance-owned installer and existing `panopticon.bootstrap` behavior under instance control.
- Adds no third-party runtime dependency; the launcher remains Python standard-library only.
- Establishes a small environment-variable contract shared by public and customized private installers.
