# Security and responsible testing

This tool targets an industrial controller environment. Treat it as diagnostic research code with **no safety certification**.

Never use it as part of a safety system. Do not add control/write operations. Do not run on live production equipment without explicit authorization and an isolated, reviewed procedure. A DDE `REQUEST` is client-side read-only, but it does not prove the server implementation has no side effects.

Do not disclose workstation usernames, PCU hostnames, network addresses, Windows SIDs, serial numbers, controller backups, licensing files, private logs, or site details in public issues. Redact evidence before submission. Report vulnerabilities privately to repository maintainers once contact information is established.

See [docs/safety.md](docs/safety.md).
