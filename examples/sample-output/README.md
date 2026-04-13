# Sample Output

This directory contains tracked output generated from `fixtures/sample_releases.csv` and `fixtures/sample-target.properties`.

For local database apply examples, see [`examples/direct-apply/`](../direct-apply/README.md).

Files:

- `bootstrap-dry-run.txt`: console summary from `bootstrap` dry-run mode
- `bootstrap-export-sql.txt`: console summary from `bootstrap --export-sql`
- `bootstrap-apply-postgres.txt`: console summary from `bootstrap --apply` against the PostgreSQL sample
- `bootstrap-apply-mysql.txt`: console summary from `bootstrap --apply` against the MySQL sample
- `decisions.csv`: per-row import decisions
- `review_queue.csv`: uncertain rows flagged for `REVIEW` or `FAILURE`
- `review-summary.txt`: grouped summary of review queue reasons
- `staging.csv`: normalized staging rows
- `artists.csv`: canonical artist catalog after import
- `releases.csv`: canonical release catalog after import
- `catalog.sql`: generated MySQL SQL
- `catalog.postgres.sql`: generated PostgreSQL SQL
