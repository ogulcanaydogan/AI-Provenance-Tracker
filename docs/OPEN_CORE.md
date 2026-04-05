# Open-Core Model

## Summary

WhoisFake now follows an open-core structure:

- `AI-Provenance-Tracker` stays public and MIT-licensed
- commercial differentiation moves into private repositories
- integration happens through API, artifact, and environment contracts
- git submodules are intentionally not used

This keeps the trust layer auditable while protecting the datasets, workflows, and operational knowledge that form the commercial moat.

## Repository Topology

### Public repository

- `AI-Provenance-Tracker`
  - community/core edition
  - public detection API
  - public benchmark methodology
  - public evidence schema and export format
  - baseline frontend and documentation
  - community-safe Instagram/social foundation

### Private repositories

- `whoisfake-enterprise`
  - newsroom and team workflows
  - social inbox dashboard and orchestration
  - customer auth and admin
  - billing and quota UX
  - premium managed integrations

- `whoisfake-assets`
  - proprietary datasets
  - hard-negative corpora
  - calibration bundles
  - model bundles and private artifacts
  - provider prompt and config maps

- `whoisfake-ops`
  - environment contracts
  - deployment runbooks
  - monitoring references
  - secret ownership
  - customer rollout procedures

## Public vs Private Boundary

### Keep in the public core

- detection endpoints and baseline modality routing
- evidence payload shape
- URL analysis semantics
- benchmark methodology and public quality posture
- explainability and public-facing docs
- safe acquisition features that help users try the product

### Build in private repositories

- customer-specific workflows
- private social triage and escalation logic
- enterprise admin surfaces
- premium billing and quota flows
- model/data artifacts that should not be redistributed
- deploy and incident knowledge that should not be public

## Why This Split Exists

The public repository serves three jobs:

1. credibility
2. acquisition
3. developer-facing documentation

The private repositories serve the commercial job:

1. protect the data and artifacts that improve accuracy
2. protect enterprise workflow IP
3. protect operational knowledge and customer rollout details

## Local Workspace Standard

Use sibling repositories under one workspace root:

```text
first_badge/
├── AI-Provenance-Tracker/
├── whoisfake-enterprise/
├── whoisfake-assets/
└── whoisfake-ops/
```

## Integration Contract

### Enterprise -> public core

- consumes public detection APIs
- uses public evidence payloads
- targets the public core through environment variables such as `PUBLIC_CORE_API_URL`

### Enterprise -> assets

- resolves bundle paths and versions through contract variables
- does not import assets with git submodules

### Ops -> all surfaces

- owns environment matrices
- owns secret ownership documentation
- owns deploy order and rollout runbooks

## What Does Not Change

- this repository stays public
- MIT license remains in place
- the public core remains independently runnable
- no immediate code extraction is required from the current public repo

## Current Commercial Direction

The public core remains the trust and funnel layer for:

- fact-check teams
- newsroom verification desks
- explainable authenticity analysis

The private layer becomes the monetization path for:

- team workflows
- managed social verification
- artifact-backed accuracy improvements
- customer operations and SLA-backed delivery

## Initial Build Order

1. establish private repository scaffolds
2. document public/private boundaries
3. move new commercial development into private repos
4. keep the public core stable and auditable
