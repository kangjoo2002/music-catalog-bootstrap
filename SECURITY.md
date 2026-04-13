# Security Policy

## Supported Scope

This project is a local CLI for generating bootstrap artifacts. It does not host a network service and it should not require production database credentials.

## Reporting

If you find a security issue, please avoid posting the full exploit publicly before a fix is available.

Until a dedicated security contact is added, open a private report through the repository security advisory flow if available. If that is not available, open an issue with minimal reproduction details and note that you can share more privately.

## Hardening Notes

- Target profile identifiers are validated before SQL generation.
- SQL output is generated as a file, not applied directly to a database.
- Prefer running the tool against a dedicated working directory, not a production environment.
