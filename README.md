# Music Catalog Bootstrap

[한국어](README.ko.md)

> A Python CLI for turning MusicBrainz `release` dumps into an initial music service catalog.

`Music Catalog Bootstrap` reads official MusicBrainz dumps or normalized CSV snapshots, builds a canonical catalog centered on `artist` and `release`, classifies each row as `AUTO_CREATE`, `AUTO_MATCH`, `REVIEW`, or `FAILURE`, and then runs a dry-run preview, exports SQL, or applies the result to a target schema.

Scope is limited to initial catalog bootstrap. It is not a replication pipeline or a general ETL framework.

## Features

- Supports MusicBrainz `release.tar.xz`, `release.xz`, `release.json`, and `release.jsonl`
- Supports normalized CSV snapshot imports
- Persists a cumulative canonical catalog for `artist` and `release`
- Records per-run `AUTO_CREATE`, `AUTO_MATCH`, `REVIEW`, and `FAILURE` decisions
- Exports a per-run `review_queue.csv` for uncertain records
- Supports one-step `bootstrap` runs in `dry-run`, `export-sql`, or `apply` mode
- Keeps `dry-run` previews separate from committed catalog runs
- Generates SQL or applies changes to MySQL / PostgreSQL schemas through built-in Python drivers

Architecture overview: [ARCHITECTURE.md](ARCHITECTURE.md)
Decision model: [docs/decision-model.md](docs/decision-model.md)
Review queue guide: [docs/review-queue.md](docs/review-queue.md)
Direct apply guide: [docs/direct-apply.md](docs/direct-apply.md)

## 30-Second Demo

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

Example `bootstrap` summary:

```text
Bootstrap summary

Mode:                   dry-run
Run ID:                 run_20260412_085134
Run directory:          .catalog-data/previews/run_20260412_085134

Decision summary
Input rows:             5
AUTO_CREATE:            3
AUTO_MATCH:             0
REVIEW:                 1
FAILURE:                1

Catalog state
Canonical artists:      3
Canonical releases:     3

Target
Engine:                 mysql
Artist table:           service_artists
Release table:          service_releases

Artifacts
Review queue rows:      2
Review queue:           .catalog-data/previews/run_20260412_085134/review_queue.csv
Review summary:         .catalog-data/previews/run_20260412_085134/review-summary.txt

Result
No changes have been applied.
Canonical catalog updated: no
Dry-run did not change the canonical catalog.
Run again with --export-sql or --apply when ready.
Review the flagged rows in .catalog-data/previews/run_20260412_085134/review_queue.csv.
```

## Example Input

Normalized CSV input is expected to use:

```text
source_id,artist_name,release_title,release_date,upc
```

Sample rows:

```csv
source_id,artist_name,release_title,release_date,upc
demo-001,Bjork,Debut,1993-07-05,5016958997028
demo-002,Radiohead,OK Computer,1997-05-21,724382885229
demo-003,Radiohead,OK Computer,1997-06-16,
demo-004,My Bloody Valentine,Loveless,1991-11-04,
demo-005,,Unknown Album,1991-11-04,
```

## Example Decisions Output

```csv
source_id,decision_type,reason_code,canonical_release_id
demo-001,AUTO_CREATE,NEW_RELEASE,1
demo-002,AUTO_CREATE,NEW_RELEASE,2
demo-003,REVIEW,SAME_ARTIST_TITLE_DIFFERENT_DATE,
demo-004,AUTO_CREATE,NEW_RELEASE,3
demo-005,FAILURE,MISSING_REQUIRED_FIELD,
```

## Example SQL Output

```sql
INSERT IGNORE INTO `service_artists` (`name`, `name_key`) VALUES ('Bjork', 'bjork');
INSERT IGNORE INTO `service_artists` (`name`, `name_key`) VALUES ('Radiohead', 'radiohead');

INSERT IGNORE INTO `service_releases` (`artist_id`, `title`, `title_key`, `released_on`, `upc`)
SELECT `id`, 'OK Computer', 'ok computer', '1997-05-21', '724382885229'
FROM `service_artists`
WHERE `name_key` = 'radiohead';
```

Tracked example outputs:

- [`examples/sample-output/bootstrap-dry-run.txt`](examples/sample-output/bootstrap-dry-run.txt)
- [`examples/sample-output/bootstrap-export-sql.txt`](examples/sample-output/bootstrap-export-sql.txt)
- [`examples/sample-output/bootstrap-apply-postgres.txt`](examples/sample-output/bootstrap-apply-postgres.txt)
- [`examples/sample-output/bootstrap-apply-mysql.txt`](examples/sample-output/bootstrap-apply-mysql.txt)
- [`examples/sample-output/decisions.csv`](examples/sample-output/decisions.csv)
- [`examples/sample-output/review_queue.csv`](examples/sample-output/review_queue.csv)
- [`examples/sample-output/review-summary.txt`](examples/sample-output/review-summary.txt)
- [`examples/sample-output/catalog.sql`](examples/sample-output/catalog.sql)
- [`examples/sample-output/catalog.postgres.sql`](examples/sample-output/catalog.postgres.sql)

Direct apply examples:

- [`examples/direct-apply/README.md`](examples/direct-apply/README.md)
- [`examples/direct-apply/postgresql/docker-compose.yml`](examples/direct-apply/postgresql/docker-compose.yml)
- [`examples/direct-apply/mysql/docker-compose.yml`](examples/direct-apply/mysql/docker-compose.yml)

## Installation

Requirements:

- Python 3.10 or later

Option 1. Use the GitHub Release ZIP

- download the release ZIP
- Windows: run `bin\music-catalog-bootstrap.bat`
- macOS/Linux: run `sh ./bin/music-catalog-bootstrap`
- `dry-run` and `export-sql` work without installing the package
- `--apply` needs the optional apply dependencies in the same Python environment:

```sh
python -m pip install ".[apply]"
```

Option 2. Run from source without installation

- Windows: `catalog.bat`
- macOS/Linux: `sh ./catalog`

Option 3. Install from source

```sh
python -m pip install -e .
music-catalog-bootstrap --help
```

Install apply dependencies too if you want direct database writes:

```sh
python -m pip install -e ".[apply]"
```

## Quick Start

Bundled sample files:

- MusicBrainz sample input: `fixtures/musicbrainz_release_subset.jsonl`
- CSV sample input: `fixtures/sample_releases.csv`
- MySQL target profile: `fixtures/sample-target.properties`
- PostgreSQL target profile: `fixtures/sample-target-postgres.properties`
- PostgreSQL apply profile: `fixtures/sample-target-postgres-apply.properties`
- MySQL apply profile: `fixtures/sample-target-mysql-apply.properties`

Real input data can be downloaded from:

- `https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/`
- open the latest dated directory
- download `release.tar.xz`
- this tool can read `release.tar.xz` directly

Run with normalized CSV input:

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

Run with an official MusicBrainz dump:

Windows:

```bat
catalog.bat bootstrap downloads\release.tar.xz fixtures\sample-target.properties --input-kind musicbrainz --data-dir .catalog-data
```

macOS/Linux:

```sh
sh ./catalog bootstrap downloads/release.tar.xz fixtures/sample-target.properties --input-kind musicbrainz --data-dir .catalog-data
```

Apply directly with a profile that includes `target.apply.*` settings:

```sh
sh ./catalog bootstrap downloads/release.tar.xz fixtures/sample-target-postgres-apply.properties --input-kind musicbrainz --data-dir .catalog-data --apply
```

Run a local direct-apply smoke test with Docker:

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

## Commands

| Command | Description |
| --- | --- |
| `bootstrap <input-path> <target-profile> [--data-dir DIR] [--input-kind auto\|csv\|musicbrainz] [--export-sql FILE] [--apply]` | Imports input, builds the canonical catalog, writes a `review_queue.csv`, and either dry-runs, exports SQL, or applies changes. |
| `import-musicbrainz <release-file\|release.xz\|release.tar.xz\|directory> [data-dir]` | Imports a MusicBrainz `release` dump or a directory containing a release payload. |
| `import <csv-file> [data-dir]` | Imports a normalized CSV snapshot. |
| `plan <target-profile> [data-dir]` | Validates the target profile and prints the current catalog and latest run summary. |
| `export-sql <target-profile> <output-file> [data-dir]` | Generates a SQL file from the current catalog. |

The default `data-dir` is `.catalog-data`.

## Target Profile

Example target profiles live at `fixtures/sample-target.properties`, `fixtures/sample-target-postgres.properties`, `fixtures/sample-target-postgres-apply.properties`, and `fixtures/sample-target-mysql-apply.properties`.

```properties
target.engine=mysql
target.write_mode=insert-ignore

artist.table=service_artists
artist.id.column=id
artist.lookup.column=name_key
artist.name.column=name
artist.name_key.column=name_key

release.table=service_releases
release.artist_id.column=artist_id
release.title.column=title
release.title_key.column=title_key
release.date.column=released_on
release.upc.column=upc
```

```properties
target.engine=postgresql
target.write_mode=insert-ignore
```

Optional direct-apply settings:

```properties
target.apply.mode=driver
target.apply.host=localhost
target.apply.port=55432
target.apply.database=music_app
target.apply.user=bootstrap
target.apply.password_env=MCB_PG_PASSWORD
```

Optional command-mode override:

```properties
target.apply.mode=command
target.apply.command=psql
```

## Tests

```sh
python -m unittest discover -s tests -v
```

## Build Release ZIP

- Windows: `scripts\build-release.bat`
- PowerShell: `.\scripts\build-release.ps1`
- Cross-platform: `python scripts/build-release.py`

The versioned ZIP is generated under `build/distributions/`.

## Current Scope and Limitations

- Target engines: `mysql`, `postgresql`
- Write mode: `insert-ignore`
- Entity scope: `artist`, `release`
- Direct apply uses built-in Python drivers by default and can fall back to local client commands
- Direct-apply smoke coverage runs in CI for both PostgreSQL and MySQL
- Not supported: incremental sync, `track`/`recording` focused ingestion, engines other than MySQL or PostgreSQL

## Roadmap

- release automation
- easier installation paths
- additional output targets
- broader entity coverage

## License

This repository is available under the [MIT License](LICENSE).

See also: [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), [Roadmap](ROADMAP.md), [Changelog](CHANGELOG.md)
