# Template sync recovery tasks

## 1. Repair protected-path registration

- [x] 1.1 Update the shared template-sync workflow to emit physical newline-delimited `merge=ours` entries for generated and org-declared protected paths.
- [x] 1.2 Make the local recovery commands use the same valid protected-path registration before their merge.

## 2. Make failures actionable

- [x] 2.1 Add stage-specific, valid-Markdown summaries for merge and other failure-prone template-sync operations, including the detected error and corrective action.
- [x] 2.2 Retain a valid local-recovery section that complements rather than replaces the failure cause.

## 3. Verify the workflow contract

- [x] 3.1 Extend template-sync tests to detect literal escape sequences in workflow-generated Git attributes and step-summary output.
- [x] 3.2 Verify with real Git that both-sided changes to generated and org-declared protected paths preserve the instance copy and merge successfully.
- [x] 3.3 Run the focused template-sync tests and the repository's required validation commands.

## 4. Update documentation

- [x] 4.1 Update README.md and docs/spec.md to reflect any user-facing or architectural changes introduced by this change.
