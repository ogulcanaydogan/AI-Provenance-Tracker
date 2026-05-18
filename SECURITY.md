# Security Policy

## Supported Versions

Security fixes are backported to the latest minor release on the active major
line. Older minors receive fixes for critical issues only.

| Version | Status              | Security fixes      |
| ------- | ------------------- | ------------------- |
| 1.1.x   | Pre-release         | :white_check_mark:  |
| 1.0.x   | Current stable      | :white_check_mark:  |
| 0.1.x   | Legacy              | Critical only       |
| < 0.1   | Unsupported         | :x:                 |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public issue.**

### How to Report

You have two options:

1. **GitHub Security Advisories** (preferred): use the repository's
   [private vulnerability reporting](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/security/advisories/new)
   form. This creates a private channel between you and the maintainers and
   integrates cleanly with the eventual public advisory + CVE assignment.
2. **Email**: send a detailed report to **security@ogulcanaydogan.com** with
   subject `[SECURITY] AI Provenance Tracker — <brief description>`.

In both cases, include:

- Description of the vulnerability and affected component
- Steps to reproduce, ideally as a minimal proof-of-concept
- Potential impact assessment (confidentiality, integrity, availability)
- Suggested fix or mitigation, if any
- Whether you would like to be credited in the eventual advisory

### Response Timeline

| Stage                  | Target               |
| ---------------------- | -------------------- |
| Acknowledgement        | 48 hours             |
| Initial assessment     | 5 business days      |
| Fix development        | 14 business days     |
| Coordinated disclosure | After fix is released and adopted |

For critical issues (RCE, authentication bypass, data exfiltration), the
14-day target is treated as an upper bound rather than a default.

### What to Expect

- You will receive an acknowledgement within 48 hours confirming receipt.
- We will work with you to understand the scope and severity of the issue.
- A fix will be developed and tested before any public disclosure.
- You will be credited in the release notes and the GitHub Security
  Advisory unless you prefer anonymity.

### Scope

The following surfaces are explicitly in scope:

- **Backend API** (`backend/`) — injection, authentication bypass, IDOR,
  data leakage, SSRF through URL-detection endpoints, deserialisation,
  path traversal on media uploads.
- **Webhook surface** — Stripe billing webhook signature validation
  (`X-Billing-Webhook-Secret`), Instagram webhook HMAC verification
  (`X-Hub-Signature-256`), replay protection on social-intake events.
- **API key + plan logic** — privilege escalation between `starter` /
  `pro` / `enterprise` plans, daily spend cap bypass, monthly quota
  bypass, API key enumeration.
- **Streaming endpoints** — Server-Sent Events on
  `POST /detect/stream/text` (resource exhaustion, prompt-injection that
  leaks across SSE channels).
- **X (Twitter) intelligence pipeline** — credential exposure on the
  configured `X_BEARER_TOKEN`, scheduler abuse, drilldown SSRF.
- **Frontend** (`frontend/`) — XSS, CSRF, open redirect, sensitive
  data exposure, prototype pollution.
- **Docker configurations** — container escape, privilege escalation,
  image supply-chain (registry pinning, build provenance).
- **CI/CD pipelines** — secret leakage in workflow logs, supply chain
  via untrusted actions, branch-protection bypass.
- **Third-party integrations** — OpenAI / Anthropic / provider
  credential exposure, SSRF on URL fetch, prompt injection that crosses
  trust boundaries.

### Out of Scope

- Denial-of-service attacks against development or staging environments.
- Social engineering of project maintainers.
- Vulnerabilities in upstream dependencies — please report directly to
  the dependency maintainer. We track these via Dependabot and CodeQL
  and will pull in your fix once it is released upstream.
- Issues that require a fully compromised client (lost device, malware on
  the user's machine).
- Missing security headers on endpoints documented as public/static.
- Rate-limit findings that simply reproduce the documented per-plan
  limits in `docs/API.md`.

## Production Security Controls

The hosted deployment (https://whoisfake.com / https://api.whoisfake.com)
runs the following baseline:

- TLS 1.2+ enforced; HTTP redirects to HTTPS.
- Per-endpoint rate limiting with deterministic 429 responses (see
  `docs/API.md` § Rate Limits).
- Plan-aware daily spend cap and monthly request quota (see
  `docs/API.md` § Spend Control).
- Structured JSON error envelope with `request_id` for every response,
  surfacing the correlation ID without leaking internal stack traces.
- Webhook signature verification on Instagram (`X-Hub-Signature-256`)
  and Stripe-style (`X-Billing-Webhook-Secret`) inbound calls when the
  corresponding secret is configured.
- Admin endpoints gated behind `X-Social-Admin-Secret` when configured.
- Secrets injected via environment variables only — never committed to
  the repository. CI uses GitHub Actions secrets with least-privilege
  job tokens.
- Container images built reproducibly; production deployments pin image
  digests, not floating tags.

## Security Best Practices for Contributors

- Never commit secrets, API keys, or credentials. Use `.env.example` as
  the canonical template; `.env` is gitignored.
- Use environment variables for all sensitive configuration.
- Follow the principle of least privilege in Docker containers — pinned
  base images, non-root users, read-only filesystem where feasible.
- Keep dependencies up to date — Dependabot is enabled for pip, npm, and
  GitHub Actions; merge security updates promptly.
- Run `pre-commit` hooks before pushing (includes ruff, eslint, and
  secret scanning).
- New endpoints that touch billing, authentication, or admin surfaces
  must include matching tests under `backend/tests/` before merge.
