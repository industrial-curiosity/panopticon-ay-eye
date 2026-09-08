---
name: panopticon-doc-drift-batch-planning
description: Plan isolated batches for Panopticon CI doc-drift evaluation when product changes require an LLM review.
---

# Panopticon doc-drift batch plan

You receive retained behavior-bearing changed paths and available documentation
paths. Create the smallest coherent batches that let a separate evaluator judge
documentation drift for each change independently.

## Rules

- Assign every changed path to exactly one batch.
- Put related paths in one batch only when they implement one behavior.
- Include only documentation paths needed to judge that batch; an empty list is
  valid when no available documentation is relevant.
- Do not name paths that are absent from the supplied lists.
- Do not judge whether documentation is stale. That is the evaluator's job.

## Response contract

Respond with only this JSON object, with no prose or code fences:

```json
{
  "batches": [
    {
      "paths": ["src/api.py"],
      "docs": ["docs/components/api.md"]
    }
  ]
}
```
