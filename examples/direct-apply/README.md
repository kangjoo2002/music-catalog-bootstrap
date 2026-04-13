# Direct Apply Examples

This directory contains local database samples for `bootstrap --apply`.

The examples use Docker so you can test the full flow without touching an existing database:

1. start a local MySQL or PostgreSQL container
2. initialize a minimal music-service schema
3. run `bootstrap --apply`
4. verify that `service_artists` and `service_releases` were populated

Available examples:

- `mysql/`
  Local MySQL container on `localhost:53306`
- `postgresql/`
  Local PostgreSQL container on `localhost:55432`

Recommended helper:

- PowerShell: `scripts/smoke-apply.ps1`

Requirements:

- Docker Desktop or another local Docker engine
- Python apply dependencies installed:

```sh
python -m pip install -e ".[apply]"
```

Example:

Windows:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\scripts\smoke-apply.ps1 -Engine postgresql -Cleanup
PowerShell -ExecutionPolicy Bypass -File .\scripts\smoke-apply.ps1 -Engine mysql -Cleanup
```

macOS/Linux:

```sh
sh ./scripts/smoke-apply -Engine postgresql -Cleanup
sh ./scripts/smoke-apply -Engine mysql -Cleanup
```
