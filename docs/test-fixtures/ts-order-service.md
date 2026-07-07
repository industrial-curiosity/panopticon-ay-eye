# Fixture: ts-order-service (TypeScript)

[panopticon-test-child-b](https://github.com/industrial-curiosity/panopticon-test-child-b)

Test fixture repo representing a TypeScript order management service. Covers: internal-only interfaces, externally owned interfaces, and interfaces owned here and consumed by `py-inventory-service`.

## Purpose

Exercises Panopticon against a TypeScript repo where:
- The REST/OpenAPI parser picks up an owned API (`src/api/openapi.yaml`)
- The Kafka parser picks up an owned event topic (`src/events/kafka-topics.yaml`)
- S3, SQS, and external REST clients are extracted via LLM fallback from `infra/` YAML config files (`.ts` source files are not in the LLM fallback suffix set)
- Several interfaces have `null` owner (external services, manually managed)
- `ts-order-service` is both an API owner (consumed by Python) and a consumer (of the Python service's API)

## Repository structure

```
panopticon-test-child-b/
├── infra/
│   ├── s3-buckets.yaml           # LLM fallback — order-attachments-bucket (s3, owned)
│   ├── services.yaml             # LLM fallback — inventory-api, stripe-payments, shipping-provider-api (rest, consumer)
│   └── sqs-queues.yaml           # LLM fallback — order-processing-queue (sqs, owned)
├── src/
│   ├── api/
│   │   ├── openapi.yaml          # REST parser — orders-api (producer, owned)
│   │   └── routes/
│   │       ├── orders.ts
│   │       └── webhooks.ts
│   ├── clients/
│   │   ├── inventory.ts
│   │   ├── stripe.ts
│   │   └── shipping.ts
│   ├── events/
│   │   ├── kafka-topics.yaml     # Kafka parser — order-events (producer, owned)
│   │   └── producer.ts
│   ├── queue/
│   │   ├── processor.ts
│   │   └── worker.ts
│   └── storage/
│       └── attachments.ts
├── package.json
└── tsconfig.json
```

## Interfaces

### orders-api — owned, cross-repo

- **Type:** `rest`
- **Owner:** `ts-order-service / api`
- **Producer source:** `src/api/openapi.yaml`
- **Consumers (other repos):** `py-inventory-service` (declared in that repo's index)
- **Parser:** REST/OpenAPI — detected automatically from `openapi.yaml`
- **Category:** owned by this repo, consumed by sibling

`src/api/openapi.yaml` content outline:
```yaml
openapi: "3.0.3"
info:
  title: Orders API
  version: "1.0.0"
# panopticon-interface orders-api
paths:
  /orders:
    get: ...
    post: ...
  /orders/{id}:
    get: ...
    patch: ...
  /orders/{id}/cancel:
    post: ...
```

### order-events — owned, cross-repo

- **Type:** `kafka`
- **Owner:** `ts-order-service / events`
- **Producer source:** `src/events/kafka-topics.yaml`
- **Consumers (other repos):** `py-inventory-service`
- **Parser:** Kafka topic-config — detected automatically
- **Category:** owned by this repo, consumed by sibling

`src/events/kafka-topics.yaml` content outline:
```yaml
# panopticon-interface order-events
topics:
  - name: order-events
    partitions: 12
    replication_factor: 3
    config:
      retention.ms: "604800000"
      cleanup.policy: delete
```

### order-processing-queue — internal only

- **Type:** `sqs`
- **Owner:** `panopticon-test-child-b / queue` (LLM-inferred component)
- **Extraction source:** `infra/sqs-queues.yaml`
- **Consumers (other repos):** none
- **Parser:** none — LLM fallback; hint in config file pins the name
- **Category:** internal; never crosses repo boundaries

`infra/sqs-queues.yaml` content outline:
```yaml
queues:
  # panopticon-interface order-processing-queue
  - name: order-processing-queue
    type: sqs
    visibility_timeout_seconds: 300
    receive_wait_time_seconds: 20
```

### order-attachments-bucket — internal only

- **Type:** `s3`
- **Owner:** `panopticon-test-child-b / storage` (LLM-inferred component)
- **Extraction source:** `infra/s3-buckets.yaml`
- **Consumers (other repos):** none
- **Parser:** none — LLM fallback; hint in config file pins the name
- **Category:** internal; used for temporary file storage (receipts, uploads)

`infra/s3-buckets.yaml` content outline:
```yaml
buckets:
  # panopticon-interface order-attachments-bucket
  - name: order-attachments-bucket
    versioning: false
    lifecycle_expiration_days: 7
```

### inventory-api — external to this repo, owned by sibling

- **Type:** `rest`
- **Owner:** `null` in this repo's index (truth lives in `py-inventory-service`)
- **Extraction source:** `infra/services.yaml`
- **Category:** cross-repo; ownership declared by `panopticon-test-child-a`

### stripe-payments — external service, manually managed

- **Type:** `rest`
- **Owner:** `null` (third-party, no Panopticon owner)
- **Extraction source:** `infra/services.yaml`
- **Category:** external; owner is Stripe, not any org repo

### shipping-provider-api — external service, manually managed

- **Type:** `rest`
- **Owner:** `null` (third-party, no Panopticon owner)
- **Extraction source:** `infra/services.yaml`
- **Category:** external; manually managed contract with shipping vendor

`infra/services.yaml` content outline (covers all three consumer entries above):
```yaml
services:
  # panopticon-interface inventory-api
  inventory:
    base_url: ${INVENTORY_API_URL}
  # panopticon-interface stripe-payments
  stripe:
    base_url: https://api.stripe.com/v1
  # panopticon-interface shipping-provider-api
  shipping:
    base_url: ${SHIPPING_API_URL}
```

## Expected `panopticon/index.json`

Repo name in the index is the GitHub repo name: `panopticon-test-child-b`. Entries marked `extracted_by: "llm"` come from LLM fallback over `infra/` config files. Deterministic-parser entries have no `extracted_by`. Component falls back to the repo name when the parser cannot infer it; LLM extraction uses the component inferred from the config file structure.

```json
{
  "interfaces": {
    "inventory-api": [
      {
        "consumer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/services.yaml"]
          }
        ],
        "extracted_by": "llm",
        "owner": null,
        "producer": [],
        "type": "rest"
      }
    ],
    "order-attachments-bucket": [
      {
        "consumer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/s3-buckets.yaml"]
          }
        ],
        "extracted_by": "llm",
        "owner": {
          "component": "storage",
          "repo": "panopticon-test-child-b"
        },
        "producer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/s3-buckets.yaml"]
          }
        ],
        "type": "s3"
      }
    ],
    "order-events": [
      {
        "consumer": [],
        "owner": {
          "component": "panopticon-test-child-b",
          "repo": "panopticon-test-child-b"
        },
        "producer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["src/events/kafka-topics.yaml"]
          }
        ],
        "type": "kafka"
      }
    ],
    "order-processing-queue": [
      {
        "consumer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/sqs-queues.yaml"]
          }
        ],
        "extracted_by": "llm",
        "owner": {
          "component": "queue",
          "repo": "panopticon-test-child-b"
        },
        "producer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/sqs-queues.yaml"]
          }
        ],
        "type": "sqs"
      }
    ],
    "orders-api": [
      {
        "consumer": [],
        "owner": {
          "component": "panopticon-test-child-b",
          "repo": "panopticon-test-child-b"
        },
        "producer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["src/api/openapi.yaml"]
          }
        ],
        "type": "rest"
      }
    ],
    "shipping-provider-api": [
      {
        "consumer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/services.yaml"]
          }
        ],
        "extracted_by": "llm",
        "owner": null,
        "producer": [],
        "type": "rest"
      }
    ],
    "stripe-payments": [
      {
        "consumer": [
          {
            "repo": "panopticon-test-child-b",
            "source_files": ["infra/services.yaml"]
          }
        ],
        "extracted_by": "llm",
        "owner": null,
        "producer": [],
        "type": "rest"
      }
    ]
  },
  "schema_version": 1
}
```

## Panopticon test coverage

| Scenario | Interface | Detail |
|---|---|---|
| Deterministic parser (REST) | `orders-api` | `src/api/openapi.yaml` matched by REST parser; component falls back to repo name |
| Deterministic parser (Kafka) | `order-events` | `src/events/kafka-topics.yaml` matched by Kafka parser; `partitions:` present → producer |
| LLM fallback + hint | `order-processing-queue` | `infra/sqs-queues.yaml` fed to LLM; hint pins name; entry tagged `extracted_by: "llm"` |
| LLM fallback + hint | `order-attachments-bucket` | `infra/s3-buckets.yaml` fed to LLM; hint pins name; entry tagged `extracted_by: "llm"` |
| LLM fallback + hint (multi) | `inventory-api`, `stripe-payments`, `shipping-provider-api` | All three consumer entries extracted from `infra/services.yaml` in one LLM pass |
| Internal-only | `order-processing-queue`, `order-attachments-bucket` | Owner = this repo; no other repo's index references them; no conflicts possible |
| External / null owner | `stripe-payments`, `shipping-provider-api` | `owner: null`; compile step never generates ownership conflict for these |
| Cross-repo: this owns, sibling consumes | `orders-api`, `order-events` | Compiled index merges this shard's ownership with `panopticon-test-child-a`'s consumer entries |
| Cross-repo: sibling owns, this consumes | `inventory-api` | `owner: null` locally; compiled index defers ownership to `panopticon-test-child-a`'s shard |
