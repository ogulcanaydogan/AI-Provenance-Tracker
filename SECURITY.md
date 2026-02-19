# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public issue.**

### How to Report

1. **Email**: Send a detailed report to **security@ogulcanaydogan.com**
2. **Subject**: `[SECURITY] AI Provenance Tracker — <brief description>`
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if any)

### Response Timeline

| Stage                  | Target     |
| ---------------------- | ---------- |
| Acknowledgement        | 48 hours   |
| Initial assessment     | 5 business days |
| Fix development        | 14 business days |
| Public disclosure      | After fix is released |

### What to Expect

- You will receive an acknowledgement within 48 hours confirming receipt.
- We will work with you to understand the scope and severity of the issue.
- A fix will be developed and tested before any public disclosure.
- You will be credited in the release notes unless you prefer anonymity.

### Scope

The following are in scope:

- Backend API (`backend/`) — injection, authentication bypass, data leakage
- Frontend (`frontend/`) — XSS, CSRF, sensitive data exposure
- Docker configurations — container escape, privilege escalation
- CI/CD pipelines — secret leakage, supply chain attacks
- Third-party API integrations — credential exposure, SSRF

### Out of Scope

- Denial of service attacks against development/staging environments
- Social engineering of project maintainers
- Vulnerabilities in upstream dependencies (report these to the dependency maintainer)

## Security Best Practices for Contributors

- Never commit secrets, API keys, or credentials
- Use environment variables for all sensitive configuration
- Follow the principle of least privilege in Docker containers
- Keep dependencies up to date (Dependabot is enabled)
- Run `pre-commit` hooks before pushing (includes secret scanning)
