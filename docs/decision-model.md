# Decision Model

Music Catalog Bootstrap does not treat every input row the same way.

Each imported row is classified into one of four outcomes:

- `AUTO_CREATE`
  A new canonical catalog row can be created safely.
- `AUTO_MATCH`
  The input matches an existing canonical release.
- `REVIEW`
  The row looks valid, but the match is uncertain and should be checked by a human.
- `FAILURE`
  The row is missing required information or cannot be mapped safely.

## Why This Matters

Bootstrapping a music service catalog is rarely a clean “load everything” problem.

Public metadata is incomplete, release dates are inconsistent, and duplicate-looking rows are common. A decision model makes the bootstrap step explicit:

- safe rows are handled automatically
- uncertain rows are surfaced in `review_queue.csv`
- invalid rows are kept visible instead of disappearing silently

## Current Review Reasons

- `SAME_ARTIST_TITLE_DIFFERENT_DATE`
  The same artist/title combination already exists, but the release date differs.
- `MISSING_REQUIRED_FIELD`
  The input row is missing an artist or release title.

The current implementation keeps the decision model intentionally small and predictable. The goal is not to automate every edge case. The goal is to make the bootstrap step rerunnable and understandable.
