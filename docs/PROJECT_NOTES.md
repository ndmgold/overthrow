# Overthrow: project notes

Overthrow is an IPL-only cricket stats website built on CricSheet ball-by-ball data. This repository holds the cleaned data, the bowler-style table, the scripts that rebuild it all from the raw CricSheet IPL zip, and the decisions made so far. These notes are the source of truth for every counting rule. Read them before writing any query.

The name comes from the first question asked of the data: finding legal deliveries that went for five, which almost always means a run plus four overthrows.

## What the site will be

There will be six sections sharing one data engine:

1. **Explorer**, a query playground. You pick filters (season, team, phase, venue, chasing or defending) and a stat (runs, SR, average, boundary %, non-boundary runs, dot %, wickets, economy), and get a ranked table.
2. **Players**, a profile per player: season by season, pace and spin splits, phase splits, best and worst matchups.
3. **Matches**, a replay per game: worm chart, Manhattan, ball-by-ball log, and a win-probability line.
4. **Season races**, an animated Orange Cap / Purple Cap race through each season, plus streaks such as "top scorer for their team".
5. **Trivia**, a daily question generated from real queries.
6. **Records**, fixed leaderboards kept separate from Explorer, like ESPNcricinfo's records pages next to Statsguru. Each record is a saved SQL query run in the browser, so records update with new seasons and follow the counting conventions. They cover:
   - **Batting:** most runs, highest scores, best average and strike rate, 50s and 100s, fastest 50s and 100s, most sixes, ducks.
   - **Bowling:** most wickets, best figures, best economy and strike rate, dot balls, maidens, hat-tricks, 4- and 5-wicket hauls, most expensive spells.
   - **Team:** highest and lowest totals, highest successful chases, biggest and narrowest wins, powerplay and death-over records.
   - **Partnerships:** highest overall and for each wicket, best pairs.
   - **Results:** franchise and head-to-head records, ties and super overs.
   - **By bowling style:** for example, most runs against leg-spin.
   - **Oddities:** five-run deliveries, longest overs.

   Fielding records are out, because fielding is parked. Captaincy records are out, because CricSheet doesn't mark captains.

Player names link to profiles, and matches in a player's history link to replays.

**Architecture:**
- The site is a single self-contained HTML page. It can be hosted for free on GitHub Pages straight from this repository; that decision will be made when the site is built.
- The Parquet files load once in the browser, and **DuckDB-WASM** runs SQL on them there. There's no server.
- The ball-by-ball file is about 2 MB. Expect a first-load delay of a few seconds while the engine loads.

**Build order:** Explorer and Players first, one section at a time, checking each with the user before moving on. Records comes later; the user has asked for nothing to be built yet.

## Contents

| Path | What it is |
|---|---|
| `data/balls.parquet` | Every IPL delivery, 2008–2026: 295,669 rows |
| `data/matches.parquet` | One row per IPL match: 1,242 rows |
| `data/match_players.parquet` | Everyone who took part in each match, including impact players: 27,887 rows |
| `data/bowler_styles.csv` | Bowling style for all 576 IPL bowlers, all confirmed |
| `scripts/build_db.py` | Rebuilds the three Parquet files from the CricSheet IPL JSON folder |
| `scripts/ipl_bowlers.py` | Lists every IPL bowler with CricSheet and ESPNcricinfo IDs (needs `people.csv`) |
| `scripts/build_styles.py` | Builds `bowler_styles.csv` from the tag files |
| `reference/style_tags.txt`, `style_updates.txt` | The bowler-style tags; the updates file overrides the first one |
| `reference/people.csv` | CricSheet's player register |
| `reference/ipl_bowlers.csv` | Intermediate output of `ipl_bowlers.py` |
| `reference/cricsheet/` | CricSheet's licence and the IPL archive README |

**To rebuild from the raw zip:**
```
python3 -I scripts/build_db.py <ipl_json_folder> data --ipl
python3 -I scripts/ipl_bowlers.py <ipl_json_folder> reference/people.csv reference/ipl_bowlers.csv
python3 -I scripts/build_styles.py reference/ipl_bowlers.csv reference/style_tags.txt reference/style_updates.txt data/bowler_styles.csv
```
These need `pandas`, `pyarrow`, and `duckdb` for querying.

## Key columns

**balls.parquet**
- **Position:** `over` is 0-based, so over 0 is the 1st over. `ball` counts legal deliveries only. `seq` is the delivery's order within the over, including extras. `legal` is false for wides and no-balls.
- **Players:** `batter`, `non_striker`, `bowler`, `player_out`, each paired with an `_id` column holding the CricSheet person ID.
- **Runs:** `batter_runs`, `extras`, `total_runs`, plus `wides`, `noballs`, `byes`, `legbyes` and `penalty`. `non_boundary` is true when a 4 or 6 was all run rather than hit to the rope.
- **Wickets:** `wicket` (bool), `bowler_wickets` (dismissals credited to the bowler), `wicket_kind`, `fielders`. Balls with more than one dismissal use `;`-separated values.
- **Other:** `super_over` (bool), `target_runs` and `target_overs` (on every second-innings ball, after any revision).

**matches.parquet**
- **Result:** `winner`, `result` (`tie` or `no result`), `method` (`D/L` etc.), `eliminator` (super-over winner of a tie), `win_by_runs`, `win_by_wickets`.
- **Context:** `season` (calendar year), `event`, `stage` (playoff stage, if any), `venue`, `toss_winner`, `toss_decision`, `player_of_match`, `overs_limit`.

**match_players.parquet**
- `match_id`, `team`, `player`, `player_id`: everyone CricSheet lists as taking part, with 11 starters per side.
- `joined` is `xi`, `impact_player` or `concussion_substitute`. For the player taken off, `left_reason` gives the reason and `replaced_by` gives who replaced them.
- Use this table for matches played, including players who only fielded.

**bowler_styles.csv**
- **IDs:** `identifier` (join on `balls.bowler_id`), `key_cricinfo`, `scorecard_names`.
- **Style:** `type` (Pace / Spin / Mixed), `arm`, `style`, `code`.
- **Career:** IPL balls, wickets, seasons and teams. These follow the counting conventions below: super overs and the voided 2025 match are excluded, and the bowler-wicket rule is the same as in `balls.parquet`. The columns are checked to match `balls.parquet` exactly for all 576 bowlers.

## Counting conventions (used in every answer so far)

- **Balls faced:** every delivery except wides. No-balls count as faced.
- **Batting dismissals:** everything except retired hurt and retired not out. Run-outs count.
- **Bowler wickets:** exclude run out, retired hurt, retired out, retired not out, obstructing the field, timed out and hit the ball twice.
- **Economy:** wides and no-balls count against the bowler; byes and leg byes don't.
- **Super overs:** left out of all stats. A tie won in a super over counts as a win for the eliminator.
- **Phases:** powerplay is overs 1–6 (`over` 0–5), middle is overs 7–15 (`over` 6–14), death is overs 16–20 (`over` 15–19). Rain-shortened games use the same fixed overs.
- **Boundary runs:** fours and sixes not flagged `non_boundary`. Everything else is a non-boundary run, including all-run fours.
- **Players:** join on IDs, never names. Two different players are both "Harmeet Singh", and Navdeep Saini and Arshad Khan each appear under two spellings.
- **Franchises:** these pairs are merged as one franchise:
  - Delhi Daredevils and Delhi Capitals
  - Kings XI Punjab and Punjab Kings
  - Royal Challengers Bangalore and Royal Challengers Bengaluru
  - the two spellings of Rising Pune Supergiant

  Deccan Chargers and Sunrisers Hyderabad stay separate, as do Gujarat Lions and Gujarat Titans.
- **Fielding: parked by the user.** There are no fielding stats for now, because the uncertainty is high and the impact small. See Data notes.
- **Records qualifiers:** averages and batting strike rates need at least 500 balls faced. Economy and bowling strike rates need at least 300 balls bowled.
- **Lowest totals:** an innings counts only if the team was all out or batted its full 20 overs. This leaves out rain-shortened innings unless all out, and innings that ended early because a chase was won. A rain-shortened innings can be spotted by `target_overs` < 20 (34 matches); a first innings that ended short of 120 legal balls without being all out is left out by the same rule.
- **Partnerships:** a partnership is the run of balls between two batters. When a batter **retires hurt** in the middle of a stand, the stand ends and the new pair starts a new partnership. Retired hurt isn't a wicket, so the new stand keeps the same wicket number, and one innings can have two separate 3rd-wicket stands. Retired hurt happens 19 times, in 19 matches. Retired out is a dismissal, so it ends a stand like any other wicket. There are no retired-not-out cases in the data.
- **Season** is the calendar year of the match. CricSheet's own labels, like "2007/08" and "2020/21", are replaced.

## Bowler styles

- **Coverage:** all 576 IPL bowlers are tagged and confirmed, either by lookups or by the user directly.
  - 287 right-arm pace and 72 left-arm pace (DP Vijaykumar's right arm was confirmed by the user)
  - 79 off-spin, 65 leg-spin, 61 left-arm orthodox and 8 left-arm wrist-spin
  - 1 spinner who bowls both types (Kamindu Mendis)
  - 3 who bowled both pace and spin (Andrew Symonds, Sachin Tendulkar, Shashank Singh)
- **Mystery spinners** are tagged by their stock ball: Narine, Theekshana and Ajantha Mendis as off-spin, Varun Chakaravarthy and Digvesh Rathi as leg-spin.
- **Split by type:** pace bowls 64% of IPL deliveries and spin 36%.
- **Pace speed** (medium vs fast) was **dropped** on purpose. Most stats engines don't split it.

## Data notes

- **Completeness:** the IPL data is complete. CricSheet's README withholds nothing, every match with play has full ball-by-ball data, and Afghan players are included.
- **Abandoned games:** games abandoned without a ball bowled aren't in the data, which is why some seasons have fewer matches than scheduled. The 8 no-results where play did start are included. The 12 missing games, all league matches, were checked against the schedule:
  - 2008 #47 DD v KKR, Delhi, 22 May (rain)
  - 2009 #7 MI v RR, Durban, 21 Apr (rain); #13 CSK v KKR, Cape Town, 25 Apr (rain)
  - 2011 #20 RCB v RR, Bengaluru, 19 Apr (rain)
  - 2012 #32 KKR v Deccan Chargers, Kolkata, 24 Apr (waterlogged ground); #34 RCB v CSK, Bengaluru, 25 Apr (rain)
  - 2015 #25 KKR v RR, Kolkata, 26 Apr (wet outfield)
  - 2017 #29 RCB v SRH, Bengaluru, 25 Apr (rain)
  - 2024 #63 GT v KKR, Ahmedabad, 13 May; #66 SRH v GT, Hyderabad, 16 May; #70 RR v KKR, Guwahati, 19 May (all rain)
  - 2025 RCB v KKR, Bengaluru, 17 May (rain, no toss). CricSheet's numbering has no gap here, because the voided 8 May game takes number 58.
- **Voided 2025 game (excluded):** PBKS v DC at Dharamsala on 8 May 2025 (CricSheet match 1473495) was called off after 10.1 overs (PBKS 122/1) over security concerns, then replayed in full in Jaipur on 24 May. CricSheet keeps it as a no-result, but it isn't in the IPL's official records, so the user decided Overthrow leaves it out. `build_db.py` (`IPL_VOIDED`) and `ipl_bowlers.py` (`VOIDED`) skip it. Any future voided match goes in both lists.
- **Fielding (parked):** fielding stats were explored and then dropped by the user, for these reasons:
  - CricSheet doesn't mark wicketkeepers, so keeper catches can't be reliably separated from outfield catches. Inferring the keeper from stumpings and a keeper list still left about 50 team-matches unresolved and many more assumed, and scorecards (which mark the keeper with a dagger) can't be fetched from here.
  - 177 run outs have no fielder named.

  `balls.fielders` still holds fielder names by dismissal, but has no IDs. If fielding is revisited, CricSheet's JSON gives each fielder's registry ID and a `substitute` flag. The user's rules were to exclude substitute catches and leave run outs out.
- **Checks:** a rebuild from the raw zip (11 June 2026 archive, 1,243 matches) reproduced `balls`, `matches`, `bowler_styles.csv` and `ipl_bowlers.csv` exactly. In `match_players`, every batter, non-striker and bowler appears in their team's list, and every starting XI has 11 players.
- **Licence:** CricSheet data is under the Open Database License (ODbL). The site must credit CricSheet, and any processed data shared publicly must use the same licence.

## Open items

- Build the site, starting with Explorer and Players.
- Fit the win-probability model for match replays. The plan is a simple model on runs needed, balls left and wickets in hand, trained on the 1,242 matches.
- New seasons: when one is added, re-run the scripts and tag any new bowlers in `style_updates.txt`. `build_styles.py` stops with an error if a bowler has no tag.
