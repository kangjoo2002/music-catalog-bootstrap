# Changelog

## 0.1.0

- Initial public Python CLI release
- MusicBrainz and CSV import support
- Canonical artist/release catalog persistence
- Decision logging with `AUTO_CREATE`, `AUTO_MATCH`, `REVIEW`, `FAILURE`
- One-step `bootstrap` command with dry-run, SQL export, and direct apply modes
- Per-run `review_queue.csv` export for `REVIEW` and `FAILURE` records
- Local MySQL / PostgreSQL direct-apply Docker examples and smoke script
- Direct apply now uses built-in Python drivers by default, with optional command-mode fallback
- Apply/export failures no longer persist the canonical catalog or count as committed runs
- CI and release workflows now run PostgreSQL and MySQL direct-apply smoke coverage
- Hero SVG demo asset and expanded docs bundle in release ZIPs
- MySQL `INSERT IGNORE` SQL export
- PostgreSQL `ON CONFLICT DO NOTHING` SQL export
- Release ZIP builder
