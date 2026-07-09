# Security Policy

## Supported Versions

Only the latest stable release receives security updates. Users are strongly
encouraged to always run the most current version.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of our platform seriously. If you discover a security
vulnerability, please report it privately before disclosing it publicly.

### Email

Send details of the vulnerability to:

**security@urbanheatmitigation.org**

We will acknowledge receipt within **48 hours** and provide an initial assessment
within **5 business days**.

### PGP Encryption

For sensitive disclosures, please encrypt your report using our PGP key:

```
Fingerprint: 5A3B C8F1 9D2E 4F7A 8B6C  0D1E 2F3A 4B5C 6D7E 8F90
Key ID:      0xABCDEF1234567890
```

You can download the full public key from:
`https://keys.openpgp.org/search?q=security@urbanheatmitigation.org`

### Response Timeline

- **48 hours**: Acknowledgment of receipt
- **5 business days**: Initial assessment and severity classification
- **30 days**: Target for patch release on critical vulnerabilities
- **90 days**: Coordinated public disclosure after patch release

## Disclosure Policy

We follow a **90-day coordinated disclosure** timeline:

1. Reporter submits vulnerability details.
2. We acknowledge, assess, and begin working on a fix.
3. A patch is prepared and tested.
4. The patch is released with a security advisory.
5. After 90 days, or upon release of the patch (whichever is sooner), the
   vulnerability may be publicly disclosed.

We request that reporters allow us the full 90-day window to ensure users have
adequate time to update before details become public.

## Security Good Practices

### For Developers

- Run `pip-audit` and `npm audit` before committing dependency changes.
- Use `.env` files for local secrets; never commit them to version control.
- Enable branch protection on `main`: require PR reviews, status checks, and
  signed commits.
- Run SAST scanning via Bandit (Python) and ESLint security plugins (TypeScript).
- Use `safety check` for Python dependency vulnerability scanning.
- Keep Docker images updated and scan with `trivy` or `grype` before deployment.

### For Deployment

- Never run the application as root. Use the provided `docker-compose` user
  configuration.
- Rotate API keys and database passwords on a regular schedule (90 days max).
- Enable TLS 1.3 for all production endpoints.
- Use rate limiting on all API routes (already configured in Nginx).
- Enable audit logging for all data access and administrative actions.
- Restrict database access to the application service only (no public ports).
- Use Redis with authentication and TLS in production.
- Configure Prometheus and Grafana dashboards with authentication.
- Regularly back up the PostgreSQL database and test restoration procedures.

### For Reporting

- **Do not** file a public GitHub issue for security vulnerabilities.
- **Do not** share vulnerability details with unauthorized parties.
- **Do** include as much context as possible: affected versions, steps to
  reproduce, potential impact, and suggested remediation if available.

We appreciate your help in keeping the Urban Heat Mitigation Platform and its
users safe.
