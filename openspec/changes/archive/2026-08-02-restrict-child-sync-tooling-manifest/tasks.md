# Implementation Tasks

## 1. Shared Manifest

- [x] 1.1 Create an instance-owned child-safe local-tooling manifest module and make bootstrap use it.
- [x] 1.2 Make sync download the instance manifest on every run before filtering, previewing, and writing modules.

## 2. Regression Coverage

- [x] 2.1 Replace complete-directory sync assertions with manifest parity, CI-only exclusion, and unmanaged-child-file preservation tests.
- [x] 2.2 Update testing and architecture documentation for the explicit local/CI tooling boundary.

## 3. Verification

- [x] 3.1 Run focused and full test suites, strict OpenSpec validation, and Markdown structure checks.
