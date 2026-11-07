# Overthrow

An IPL cricket statistics website built on ball-by-ball data. Overthrow lets fans explore every delivery bowled in the Indian Premier League since 2008: custom rankings, player profiles, match replays with win probability, season races, a daily trivia question and an all-time records section, all without writing code.

The whole site will run in the browser. The data is stored as Parquet files and queried with [DuckDB-WASM](https://github.com/duckdb/duckdb-wasm), so no server is needed.

## Status

The site is in the planning stage. The cleaned dataset and the scripts that rebuild it are in place; the website sections have not been built yet.

## Repository layout

| Path | Contents |
|---|---|
| `data/` | Cleaned IPL data: deliveries, matches, playing XIs and bowling styles |
| `scripts/` | Python scripts that rebuild `data/` from CricSheet's IPL JSON archive |
| `reference/` | Bowling-style tags, CricSheet's player register, and CricSheet's licence and README |
| `docs/PROJECT_NOTES.md` | Project plan, data dictionary and every counting rule used in the stats |

## Rebuilding the data

Download the IPL JSON archive (`ipl_json.zip`) from [CricSheet](https://cricsheet.org/downloads), unzip it into a folder, then run:

```
pip install pandas pyarrow duckdb
python3 -I scripts/build_db.py <ipl_json_folder> data --ipl
python3 -I scripts/ipl_bowlers.py <ipl_json_folder> reference/people.csv reference/ipl_bowlers.csv
python3 -I scripts/build_styles.py reference/ipl_bowlers.csv reference/style_tags.txt reference/style_updates.txt data/bowler_styles.csv
```

## Data source and licence

Ball-by-ball data comes from [CricSheet](https://cricsheet.org/), which is made available under the [Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/summary/). The processed data in `data/` and `reference/` is derived from CricSheet and is shared under the same licence. See `reference/cricsheet/LICENSE.txt`.
