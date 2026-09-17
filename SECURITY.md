# Security Policy

## Supported Versions

Security updates and patches are actively maintained for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## Credential Safety Guidelines

PitchFlow interacts with external email providers (Gmail SMTP/IMAP) and Notion APIs. To keep your account secure:

1. **Local-Only Storage**: Your Google App Passwords and API tokens are persisted only on your local machine in `data/app_config.json`.
2. **Git Protection**: `data/app_config.json` is strictly added to `.gitignore`. Never use `git add -f` to force-commit this file to any public repository.
3. **App Passwords**: Always use a dedicated 16-character [Google App Password](https://myaccount.google.com/apppasswords) rather than your main Google account password. App Passwords can be revoked at any time from your Google Security console.

---

## Reporting a Vulnerability

If you discover a potential security vulnerability within PitchFlow:

1. **Do not open a public issue**: Please refrain from creating public GitHub issues for sensitive security vulnerabilities.
2. **Contact via Email**: Privately notify the project maintainer by sending details to [karan5028ji@gmail.com](mailto:karan5028ji@gmail.com).
3. **Information to include**:
   - Description of the vulnerability and its potential impact.
   - Steps or proof-of-concept to reproduce the behavior.
   - Any suggested mitigations or patches.

You will receive an initial response within **48 hours** with an assessment and timeline for a patch.
