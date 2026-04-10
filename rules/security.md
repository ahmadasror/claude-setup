# Security Rules

1. **No hardcoded secrets** — All credentials via environment variables
2. **Parameterized queries only** — Never concatenate SQL strings
3. **Input validation at boundaries** — Validate all external input at handler level
4. **Rate limiting** — All public endpoints must have rate limits
5. **JWT best practices** — Short-lived access tokens, refresh tokens, secure signing algorithm
6. **Error sanitization** — Never expose stack traces, internal paths, or DB errors to clients
7. **CORS whitelist** — Only allow specific origins, never wildcard in production
8. **File uploads** — Validate MIME type, size limits, scan for malware
9. **Audit logging** — Log all authentication events and admin actions
