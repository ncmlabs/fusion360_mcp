# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please email us at **security@ncmlabs.com** with:

1. **Description** of the vulnerability
2. **Steps to reproduce** the issue
3. **Potential impact** assessment
4. **Suggested fix** (if you have one)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 7 days
- **Resolution Timeline**: We aim to resolve critical issues within 30 days
- **Disclosure**: We will coordinate with you on public disclosure timing

### Scope

This security policy applies to:

- The MCP Server (`Server/` directory)
- The Fusion 360 Add-in (`FusionAddin/` directory)
- Official releases and distributions

### Out of Scope

- Vulnerabilities in Autodesk Fusion 360 itself (report to Autodesk)
- Vulnerabilities in third-party dependencies (report to maintainers, but let us know)
- Issues in forked repositories

## Security Best Practices

When using this software:

- Keep the MCP server running only on localhost
- Do not expose the add-in's HTTP endpoint to untrusted networks
- Keep your Fusion 360 and Python installations up to date
- Review AI assistant actions before confirming destructive operations

## Recognition

We appreciate security researchers who help keep this project safe. With your permission, we will acknowledge your contribution in our release notes.
