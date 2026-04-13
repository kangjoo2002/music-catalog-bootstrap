# Review Queue

Every bootstrap run writes `review_queue.csv` and `review-summary.txt` into the run directory.

These files exist so teams only inspect the uncertain rows instead of re-reading the whole import.

## Files

- `review_queue.csv`
  Row-level details for `REVIEW` and `FAILURE` outcomes.
- `review-summary.txt`
  A compact summary grouped by decision reason, plus the first few flagged rows.

## `review_queue.csv` Columns

- `line_number`
- `source_id`
- `decision_type`
- `reason_code`
- `artist_name`
- `release_title`
- `release_date`
- `upc`
- `candidate_release_id`
- `candidate_artist_name`
- `candidate_release_title`
- `candidate_release_date`

Candidate columns are populated when the tool found an existing canonical release that looks close enough to require human review.

## Typical Flow

1. Run `bootstrap` without `--apply`.
2. Inspect `review-summary.txt` to understand the size of the uncertain set.
3. Open `review_queue.csv` for the exact rows that need review.
4. Fix source data or adjust your bootstrap strategy.
5. Rerun with `--export-sql` or `--apply` when the result looks acceptable.

This keeps review focused on the rows that actually need attention.
