# Organization-aware interface naming proposal

## Why

Locally meaningful interface names can be generic across an organization and silently fuse
unrelated same-type resources when their shards merge. Local documentation generation needs the
instance's current index to make durable, organization-scale naming decisions, while pull requests
need a clear preview of the proposed merged architecture and its risks.

## What Changes

- Make local interface naming and documentation generation consult the instance compiled interface
  index before minting a new canonical name, then persist the decision as a source/configuration
  hint.
- Require inferred names to be organization-scale and non-generic: use technology plus function
  for shared infrastructure, durable owner plus surface for local interfaces, and distinct
  contract names when one backend serves multiple contracts.
- Extend PR evaluation with bounded AI-assisted candidate comparison against the instance index;
  retain deterministic merge simulation as the authoritative merge result.
- Add the child repository's committed override for the interface-conflict gating mode, taking
  precedence over the instance default. The default remains advisory; advisory and blocking modes
  both publish prominent warnings.
- Add the child repository's detailed Mermaid architecture diagram and prospective merge findings
  to the maintained Panopticon PR report comment.

## Capabilities

### New Capabilities

- `org-aware-interface-naming`: Instance-index-informed local naming, durable hint persistence,
  and naming rules that prevent generic canonical names.

### Modified Capabilities

- `interface-indexing`: Canonical-name judgment and conflict handling incorporate organization
  context while deterministic extraction and compilation remain reproducible.
- `doc-generation`: Documentation generation obtains and uses the instance compiled index before
  producing index-derived documentation.
- `pr-evaluation`: PR reports add candidate-match analysis, child override gating, and Mermaid
  architecture visibility.
- `repo-initialization`: Child configuration records and validates the optional interface-conflict
  gating override.

## Impact

Affected areas include interface naming and extraction skills, local configuration validation,
index/merge report tooling, all provider PR workflows, PR report rendering, generated-documentation
guidance, setup/reference documentation, and their Python/workflow tests.
