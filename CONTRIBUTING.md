# Contributing

Thanks for considering a contribution.

## Before Opening a PR

- Open an issue first for major scope changes.
- Keep the tool focused on music catalog bootstrap flows, not broad ETL platform scope.
- Prefer small PRs with one visible outcome.

## Local Setup

Requirements:

- Python 3.10+

Install and run tests:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

Install apply dependencies too if you want to run direct-apply smoke checks:

```sh
python -m pip install -e ".[apply]"
```

Run the sample flow:

Windows:

```bat
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data
catalog.bat bootstrap fixtures\sample_releases.csv fixtures\sample-target.properties --data-dir .catalog-data --export-sql out\catalog.sql
```

macOS/Linux:

```sh
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data
sh ./catalog bootstrap fixtures/sample_releases.csv fixtures/sample-target.properties --data-dir .catalog-data --export-sql out/catalog.sql
```

## Scope Guardrails

- Supported targets today: MySQL and PostgreSQL with `insert-ignore`
- Supported entities today: `artist`, `release`
- Preferred additions: better docs, packaging, example outputs, validation, and one carefully chosen bootstrap capability

## PR Expectations

- Add or update tests for behavior changes.
- Update `README.md` if the user-facing workflow changes.
- Keep fixtures deterministic.
- Keep smoke scripts and release bundle behavior aligned with the documented flow.

## Release Bundle

```sh
python scripts/build-release.py
```

## Prepublish Check

```sh
python scripts/prepublish-check.py
```
