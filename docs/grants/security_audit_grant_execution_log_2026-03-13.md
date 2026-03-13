# Security Audit & Grant Applications - Execution Log (2026-03-13)

## Completed Execution Actions

1. Verified VAOL workflow baseline on GitHub.
   - Repository: `ogulcanaydogan/Verifiable-AI-Output-Ledger`
   - Current workflows found: `ci.yml`, `ghcr-smoke.yml`, `release.yml`
   - Scorecard workflow is not yet present in VAOL.

2. Executed Huntr onboarding outreach for VAOL + Tier-1 set.
   - Channel: `https://huntr.com/contact-us`
   - Submission status: **sent successfully**
   - UI confirmation observed: `Message sent! We'll be in touch soon...`
   - Included repositories:
     - `ogulcanaydogan/Verifiable-AI-Output-Ledger`
     - `ogulcanaydogan/AI-Provenance-Tracker`
     - `ogulcanaydogan/LLM-Supply-Chain-Attestation`
     - `ogulcanaydogan/Sovereign-RAG-Gateway`
     - `ogulcanaydogan/Prompt-Injection-Firewall`

3. Executed cross-repo rollout audit (Tier-1 + Tier-2).
   - Script: `scripts/grants_rollout_audit.py`
   - Outputs:
     - `docs/grants/security_audit_grant_rollout_status_2026-03-13.json`
     - `docs/grants/security_audit_grant_rollout_status_2026-03-13.md`

## Submission Blocking Findings

1. OpenSSF Best Practices badge submission is currently blocked by interactive authentication.
   - URL: `https://www.bestpractices.dev/en/projects/new`
   - Observed state: `Please sign in to add a project!` (GitHub/custom login required)

2. AISI grant URL in existing docs is stale.
   - Referenced URL: `https://find-government-grants.service.gov.uk/grants/aisi-challenge-fund-1`
   - Observed state: `Page not found` (404)
   - Portal keyword checks (`AISI`, `AI Safety`, `safety institute`) returned `0` active results at execution time.

3. NLnet proposal endpoint is available but still requires manual form completion.
   - URL: `https://nlnet.nl/propose/`
   - HTTP status during execution: `200`

## Resulting Rollout Status

- VAOL external onboarding execution started (Huntr contact submitted).
- BestPractices and grant forms are prepared but not auto-submittable without interactive account/session steps.
- Tier-1/Tier-2 readiness matrix is now generated and actionable for staged rollout.

