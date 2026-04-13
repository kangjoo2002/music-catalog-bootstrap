# Direct Apply

Music Catalog Bootstrap can apply generated SQL directly through built-in Python database drivers.

`bootstrap --apply` now uses:

- `psycopg` for PostgreSQL
- `mysql-connector-python` for MySQL

You do not need local `psql` or `mysql` client binaries for the default apply flow.

You do need the optional apply dependencies installed in the active Python environment:

```sh
python -m pip install -e ".[apply]"
```

## Required Target Profile Settings

Add the following keys to a target profile when you want `bootstrap --apply`:

```properties
target.apply.mode=driver
target.apply.host=localhost
target.apply.port=55432
target.apply.database=music_app
target.apply.user=bootstrap
target.apply.password_env=MCB_PG_PASSWORD
```

`target.apply.password_env` points to an environment variable that must exist before you run the command.

## Optional Command Mode

If you want to force local client commands instead of Python drivers, set:

```properties
target.apply.mode=command
target.apply.command=psql
```

Command mode is kept as a compatibility path. Driver mode is the default recommendation.

## Local Sample Environments

Ready-to-run Docker examples live in:

- `examples/direct-apply/postgresql/`
- `examples/direct-apply/mysql/`

Matching sample profiles live in:

- `fixtures/sample-target-postgres-apply.properties`
- `fixtures/sample-target-mysql-apply.properties`

## PowerShell Smoke Test

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

The smoke script:

1. starts the matching Docker container
2. sets the expected password environment variable
3. runs `bootstrap --apply`
4. verifies inserted row counts inside the container

The same smoke flow is also executed in CI.

## Notes

- PostgreSQL sample port: `55432`
- MySQL sample port: `53306`
- Both samples use `bootstrap` / `bootstrap` as the local database credentials
