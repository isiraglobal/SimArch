# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

The SimArch core maintainers take security and privilege separation seriously. Because SimArch controls autonomous digital workers and executes task workflows, any issue allowing unauthorized privilege escalation, path traversal, or credential exposure is considered a high-priority vulnerability.

### How to Report
- **Do not report security vulnerabilities through public GitHub issues.**
- Please email details of the vulnerability to: `security@simarch.org`.
- Include a minimal reproducible proof-of-concept where feasible.
- We will acknowledge receipt of your vulnerability report within 48 hours and provide a regular status update on remediation efforts.

### Scope of Security Protections
- **Role Permissions**: Workers must never be able to execute tools not explicitly granted in their role contracts.
- **Path Traversal**: Workspace managers must restrict file reading, writing, and deletion strictly inside sandboxed workspace root directories.
- **Audit Immutability**: All material transitions and reviews must append to the immutable audit log.
