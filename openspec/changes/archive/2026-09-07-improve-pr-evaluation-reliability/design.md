# PR-evaluation reliability design

## Context

PR evaluation deliberately runs independent checks before one final gate. Today, an LLM-backed check both emits a GitHub error command and returns an operational-failure exit code; its workflow wrapper emits another error command, and the final gate emits a third. Tooling currency similarly emits one warning annotation per advisory finding. Doc drift sends the diff with every Markdown document up to a 200 KB cap, even though `interfaces.md` is deterministic and component documentation can often be selected from explicit source-path references.

The change must preserve provider-neutral LLM behavior, the existing `0`/`2`/operational-failure exit-code contract, full combined-report detail, advisory tooling-currency semantics, and all three provider workflows' equivalent PR-evaluation behavior.

## Goals / Non-Goals

**Goals:**

- Emit one Panopticon-authored blocking annotation for each operationally failed check.
- Preserve the complete operational-failure reason in the combined report and PR comment.
- Emit one tooling-currency warning per run while retaining every individual finding in the job summary.
- Reduce doc-drift request size without omitting a document when deterministic relevance cannot be proved.
- Make LLM request capacity failures diagnosable without exposing credentials or prompt content.

**Non-Goals:**

- Change org gating policy, retry budgets, provider selection, or job-timeout configuration.
- Make advisory tooling currency block a PR or add it to the mandatory-action TL;DR.
- Introduce an LLM fallback, external telemetry dependency, or a new per-child configuration field.
- Change the source of truth for deterministic `interfaces.md` rendering.

## Decisions

### Centralize workflow annotations

Check CLIs will retain their exit code and report-file behavior but will output a plain diagnostic rather than a GitHub workflow command. The provider workflow's wrapper step records only machine-readable status. The final gate emits the sole Panopticon-authored `::error::` annotation for an operationally failed check and exits nonzero after all independent checks and reporting have completed. GitHub may still display its own failed-step status.

This keeps local CLI use readable, prevents duplicate annotations, and maintains one place that maps check outcomes to workflow failure.

### Aggregate advisory tooling output

`tooling_currency` will produce a renderable list of findings. The workflow will append that list to the job summary and emit one warning containing the count and the existing sync recovery direction. A clean run emits no warning. Notices about protected-path ownership remain informational and do not count as drift findings.

Putting file-level detail in the summary preserves diagnosis while keeping the annotations panel compact. The combined PR TL;DR remains unchanged because the findings are advisory.

### Use relevance-first doc-drift context with a conservative fallback

Doc drift will always exclude deterministic `interfaces.md` from the LLM context. It will always include the architecture and operations documents because they describe cross-component behavior. For each component document, it will select the document when its content explicitly names a behavior-bearing changed path. If any changed behavior path lacks such a deterministic component-document match, it will include all component documents within the existing byte budget. The report diagnostics will identify which selection mode was used and the selected document paths.

The fallback is deliberately broad: reducing input size must never silently weaken the check when the repository's documentation does not establish a source-to-component link. A future metadata scheme is out of scope.

### Capture safe request diagnostics at the provider-neutral runtime boundary

The shared LLM runtime will expose a request diagnostic record to its caller after each request attempt sequence. The record includes provider identifier, model identifier, input byte count, transport attempts, elapsed duration, and an outcome class. The check report uses this record on both success and operational failure. It must exclude endpoint URLs, API keys, prompt/document content, response content, and resolved configuration values.

Capturing data at the shared runtime boundary keeps all provider adapters consistent. The report, rather than a new external telemetry system, is the durable diagnostic surface for a single CI run.

## Risks / Trade-offs

- **A repository's component docs lack explicit source references** → The deterministic fallback includes all component docs, preserving current coverage at the cost of no request-size reduction for that run.
- **A failure occurs before a runtime request is made** → The report marks diagnostics unavailable and retains the existing configuration/recovery message.
- **A provider workflow drifts from the shared behavior** → Extend provider-workflow contract tests across LiteLLM, OpenAI, and Bedrock.
- **GitHub adds a generic failed-step notice** → The change guarantees one Panopticon-authored annotation, not suppression of GitHub's own job-status UI.
