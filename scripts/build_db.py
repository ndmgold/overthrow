"""Overthrow: flatten a CricSheet JSON folder into ball-by-ball and match Parquet tables.

Usage:  python3 -I build_db.py <json_folder> <out_folder> [--ipl]

--ipl applies the IPL clean-up rules:
  * season = calendar year of the match (CricSheet labels some seasons "2007/08", "2020/21")
  * renamed franchises merged: Delhi Daredevils -> Delhi Capitals, Kings XI Punjab -> Punjab Kings,
    Royal Challengers Bangalore -> Royal Challengers Bengaluru,
    Rising Pune Supergiants -> Rising Pune Supergiant
  * Deccan Chargers / Sunrisers Hyderabad and Gujarat Lions / Gujarat Titans stay separate.
  * matches voided from the official records are dropped (see IPL_VOIDED).

Writes three tables: matches, balls (one row per delivery) and match_players (everyone who took
part in each match, with impact players and concussion substitutes marked).

Every player column has a matching *_id column holding the CricSheet person identifier
(join to people.csv and to bowler_styles.csv on these, never on names: some names are shared
by two players and some players appear under two spellings).
"""
import json, glob, os, sys
import pandas as pd

IPL_RENAMES = {
    'Delhi Daredevils': 'Delhi Capitals',
    'Kings XI Punjab': 'Punjab Kings',
    'Royal Challengers Bangalore': 'Royal Challengers Bengaluru',
    'Rising Pune Supergiants': 'Rising Pune Supergiant',
}
# Matches CricSheet keeps but the IPL's official records do not count.
IPL_VOIDED = {
    '1473495',  # PBKS v DC, Dharamsala, 2025-05-08: called off after 10.1 overs (security), replayed 2025-05-24
}
NOT_BOWLER_WICKETS = {'run out', 'retired hurt', 'retired out', 'retired not out',
                      'obstructing the field', 'timed out', 'hit the ball twice'}


def main(data_dir, out_dir, ipl):
    ren = (lambda t: IPL_RENAMES.get(t, t)) if ipl else (lambda t: t)
    balls, matches, players = [], [], []
    for f in sorted(glob.glob(os.path.join(data_dir, '*.json'))):
        m = json.load(open(f))
        swaps = {}
        info = m['info']
        reg = info.get('registry', {}).get('people', {})
        pid = lambda n: reg.get(n, '')
        mid = os.path.basename(f)[:-5]
        if ipl and mid in IPL_VOIDED:
            continue
        ev = info.get('event', {})
        oc = info.get('outcome', {})
        t1, t2 = info['teams'][0], info['teams'][1]
        season = info['dates'][0][:4] if ipl else str(info.get('season', ''))
        matches.append(dict(
            match_id=mid, date=info['dates'][0], season=season,
            gender=info.get('gender'), team_type=info.get('team_type'),
            team1=ren(t1), team2=ren(t2), venue=info.get('venue'), city=info.get('city'),
            event=ev.get('name'), match_number=ev.get('match_number'), stage=ev.get('stage'),
            toss_winner=ren(info.get('toss', {}).get('winner') or '') or None,
            toss_decision=info.get('toss', {}).get('decision'),
            winner=ren(oc.get('winner') or '') or None, result=oc.get('result'),
            method=oc.get('method'), eliminator=ren(oc.get('eliminator') or '') or None,
            win_by_runs=oc.get('by', {}).get('runs'), win_by_wickets=oc.get('by', {}).get('wickets'),
            player_of_match=';'.join(info.get('player_of_match', [])),
            overs_limit=info.get('overs')))
        for i, inn in enumerate(m.get('innings', []), 1):
            bt = inn['team']
            bw = t2 if bt == t1 else t1
            target = inn.get('target', {})
            for ov in inn.get('overs', []):
                legal = 0
                for seq, d in enumerate(ov['deliveries'], 1):
                    ex = d.get('extras', {})
                    is_legal = not ('wides' in ex or 'noballs' in ex)
                    legal += is_legal
                    w = d.get('wickets', [])
                    r = d['runs']
                    kinds = [x['kind'] for x in w]
                    balls.append(dict(
                        match_id=mid, innings=i, super_over=bool(inn.get('super_over')),
                        batting_team=ren(bt), bowling_team=ren(bw),
                        target_runs=target.get('runs'), target_overs=target.get('overs'),
                        over=ov['over'], ball=legal, seq=seq, legal=is_legal,
                        batter=d['batter'], batter_id=pid(d['batter']),
                        non_striker=d['non_striker'], non_striker_id=pid(d['non_striker']),
                        bowler=d['bowler'], bowler_id=pid(d['bowler']),
                        batter_runs=r['batter'], extras=r['extras'], total_runs=r['total'],
                        non_boundary=bool(r.get('non_boundary')),
                        wides=ex.get('wides', 0), noballs=ex.get('noballs', 0),
                        byes=ex.get('byes', 0), legbyes=ex.get('legbyes', 0),
                        penalty=ex.get('penalty', 0),
                        wicket=len(w) > 0,
                        bowler_wickets=sum(k not in NOT_BOWLER_WICKETS for k in kinds),
                        player_out=';'.join(x['player_out'] for x in w),
                        player_out_id=';'.join(pid(x['player_out']) for x in w),
                        wicket_kind=';'.join(kinds),
                        fielders=';'.join(fl.get('name', '') for x in w for fl in x.get('fielders', []))))
                    # Impact players and concussion substitutes, keyed by the player brought in.
                    for rp in d.get('replacements', {}).get('match', []):
                        swaps[(rp['team'], rp['in'])] = (rp.get('reason', ''), rp.get('out', ''))
        # Playing XIs: CricSheet lists everyone who took part, including players brought in.
        replaced = {(t, out): (why, i_n) for (t, i_n), (why, out) in swaps.items()}
        for team, plist in info.get('players', {}).items():
            for p in plist:
                joined, _ = swaps.get((team, p), ('xi', ''))
                left_reason, rep_by = replaced.get((team, p), ('', ''))
                players.append(dict(match_id=mid, team=ren(team), player=p, player_id=pid(p),
                                    joined=joined, replaced_by=rep_by, left_reason=left_reason))
            for (t, p) in swaps:
                if t == team and p not in plist:
                    print('WARNING: replacement not in players list', mid, team, p)
    os.makedirs(out_dir, exist_ok=True)
    mdf, bdf = pd.DataFrame(matches), pd.DataFrame(balls)
    pdf = pd.DataFrame(players)
    mdf.to_parquet(os.path.join(out_dir, 'matches.parquet'), index=False)
    bdf.to_parquet(os.path.join(out_dir, 'balls.parquet'), index=False)
    pdf.to_parquet(os.path.join(out_dir, 'match_players.parquet'), index=False)
    print(f'{len(mdf)} matches, {len(bdf)} deliveries, '
          f'{len(pdf)} player appearances -> {out_dir}')
    print('missing player ids:', int((bdf.bowler_id == '').sum() + (bdf.batter_id == '').sum()
                                     + (pdf.player_id == '').sum()))


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    main(a[0], a[1], '--ipl' in sys.argv)
