import json, glob, os, sys, csv
from collections import defaultdict

data_dir, people_csv, out_csv = sys.argv[1:4]
REN = {'Delhi Daredevils': 'Delhi Capitals', 'Kings XI Punjab': 'Punjab Kings',
       'Royal Challengers Bangalore': 'Royal Challengers Bengaluru',
       'Rising Pune Supergiants': 'Rising Pune Supergiant'}

# Matches the IPL's official records do not count (keep in sync with IPL_VOIDED in build_db.py).
VOIDED = {'1473495'}  # PBKS v DC, Dharamsala, 2025-05-08

people = {r['identifier']: r for r in csv.DictReader(open(people_csv))}
agg = defaultdict(lambda: dict(names=set(), balls=0, wkts=0, teams=set(), seasons=set()))
for f in glob.glob(os.path.join(data_dir, '*.json')):
    if os.path.basename(f)[:-5] in VOIDED:
        continue
    m = json.load(open(f))
    info = m['info']
    reg = info['registry']['people']
    yr = info['dates'][0][:4]
    for inn in m.get('innings', []):
        if inn.get('super_over'):  # super overs are left out of all stats
            continue
        bt = inn['team']
        bowl = [t for t in info['teams'] if t != bt][0]
        for ov in inn['overs']:
            for d in ov['deliveries']:
                pid = reg[d['bowler']]
                a = agg[pid]
                a['names'].add(d['bowler'])
                ex = d.get('extras', {})
                if 'wides' not in ex and 'noballs' not in ex:
                    a['balls'] += 1
                for w in d.get('wickets', []):
                    if w['kind'] not in ('run out', 'retired hurt', 'retired out', 'retired not out',
                                         'obstructing the field', 'timed out', 'hit the ball twice'):
                        a['wkts'] += 1
                a['teams'].add(REN.get(bowl, bowl))
                a['seasons'].add(yr)

rows = []
for pid, a in agg.items():
    p = people.get(pid, {})
    rows.append(dict(identifier=pid, name=sorted(a['names'])[0],
                     scorecard_names=';'.join(sorted(a['names'])),
                     unique_name=p.get('unique_name', ''),
                     key_cricinfo=p.get('key_cricinfo', ''),
                     balls=a['balls'], wickets=a['wkts'],
                     first=min(a['seasons']), last=max(a['seasons']),
                     teams='/'.join(sorted(a['teams'])),
                     in_register='yes' if p else 'no'))
rows.sort(key=lambda r: -r['balls'])
with open(out_csv, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(len(rows), 'bowlers;', sum(r['in_register'] == 'no' for r in rows), 'missing from register;',
      sum(not r['key_cricinfo'] for r in rows), 'without cricinfo id;',
      sum(len(agg[r['identifier']]['names']) > 1 for r in rows), 'with >1 name spelling')
