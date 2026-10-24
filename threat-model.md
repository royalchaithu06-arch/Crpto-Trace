# Threat model (starter)

## Assets
Account credentials, session tokens, investigation notes, case ownership, transaction records, audit trail, report exports.

## Threats and mitigations
- Credential guessing: bcrypt hashing; production should add distributed rate limiting and alerting.
- Broken object-level authorization: case note APIs verify ownership; add explicit case membership grants before multi-user sharing.
- SQL injection: SQLAlchemy parameterized queries.
- CSV formula injection: leading formula characters are escaped in export.
- Secret leakage: `.env` ignored; `.env.example` contains placeholders.
- XSS: React escapes ordinary text; avoid rendering untrusted HTML.
- CSRF: current API uses bearer tokens rather than cookies. If switching to cookie sessions, implement CSRF tokens and SameSite policy.
- Token theft: use HTTPS in deployment, short expiry, revocation; prefer HttpOnly cookie architecture for browser production use.
- False positives: rules include threshold and limitation explanations; no alert is treated as proof.

## Residual risks
No email verification/password reset delivery, MFA, distributed rate limiting, full migration framework, production cookie session flow, or independent penetration test is included in this starter. Do not use with sensitive real investigations before remediation and review.
