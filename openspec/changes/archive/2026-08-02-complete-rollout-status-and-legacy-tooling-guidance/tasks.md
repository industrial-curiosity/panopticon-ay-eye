# Implementation Tasks

## 1. Unmanaged tooling classification

- [x] 1.1 Add local-sync detection and advisory output for Python modules outside the remotely fetched local-tooling manifest, distinguishing instance-excluded from child-only candidates without writing or deleting either.
- [x] 1.2 Extend advisory tooling-currency detection to classify the same unmanaged Python candidates from the instance checkout.

## 2. Regression coverage

- [x] 2.1 Add sync tests for instance-excluded and child-only warnings, state-file exclusion, `--check-updates` purity, and no deletion.
- [x] 2.2 Add tooling-currency tests for both candidate classes, state-file exclusion, and non-blocking warning output.

## 3. Rollout evidence ledger

- [x] 3.1 Add a status ledger to the production rollout-hardening plan for steps 0–9, linking each completed step to its OpenSpec change and distinguishing unstarted, implemented, locally verified, and operationally proven work.
- [x] 3.2 Record that the true pre-change baseline was not captured and add the current baseline command, date, and result without presenting it as pre-change evidence.

## 4. Reviewed migration guidance

- [x] 4.1 Document the unmanaged-tooling warning classes and reviewed-removal process in `docs/setup-guide.md` and `PANOPTICON.md`; require preview, ownership/import review, separate approved removal, and child verification.
- [x] 4.2 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.

## 5. Verification

- [x] 5.1 Run focused sync and tooling-currency tests, the full Python suite, strict OpenSpec validation, and Markdown structure checks.
