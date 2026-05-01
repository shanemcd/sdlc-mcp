# Security Standards

All repositories must follow these security standards regardless of team or project.

## Dependency Management

- Pin all production dependencies to exact versions
- Run dependency vulnerability scans in CI
- Address critical CVEs within 48 hours

## Secrets

- Never commit secrets, API keys, or tokens to source control
- Use environment variables or a secrets manager
- Rotate credentials on a regular schedule

## Code Review

- All changes require at least one approved review before merge
- Security-sensitive changes require review from the security team
