"""Overthrow: build bowler_styles.csv for every IPL bowler.

Usage: python3 -I build_styles.py <ipl_bowlers.csv> <style_tags.txt> <style_updates.txt> <out.csv>

ipl_bowlers.csv comes from ipl_bowlers.py. style_tags.txt is the first-pass tagging,
style_updates.txt holds the corrections from lookups and user confirmation (it wins).
Pace speed (medium vs fast) was dropped on purpose: most stats engines don't split it.
"""
import csv, sys
from collections import Counter

bowlers_csv, tags_txt, updates_txt, out_csv = sys.argv[1:5]


def load(p):
    d = {}
    for l in open(p):
        if l.startswith('#') or not l.strip():
            continue
        n, c, f = l.strip().split('|')
        d[n] = (c, f)
    return d


tags = load(tags_txt)
tags.update(load(updates_txt))

# The two Harmeet Singhs share a scorecard name, so they are tagged by ESPNcricinfo ID.
BY_CRICINFO_ID = {
    '391128': ('RP', 'y'),   # Harmeet Singh Bansal, Deccan Chargers 2009-11 / Kings XI 2012-13
    '422847': ('SLA', 'y'),  # Harmeet Singh (2), Rajasthan Royals 2013 (user-confirmed)
}

LABEL = {'RP': 'Right-arm pace', 'LP': 'Left-arm pace', 'PACE': 'Pace (arm unconfirmed)',
         'OB': 'Off-spin', 'LB': 'Leg-spin', 'SLA': 'Left-arm orthodox', 'LWS': 'Left-arm wrist-spin',
         'SPIN': 'Spin (both types)', 'MIX': 'Mixed pace and spin'}
TYPE = {'RP': 'Pace', 'LP': 'Pace', 'PACE': 'Pace', 'OB': 'Spin', 'LB': 'Spin', 'SLA': 'Spin',
        'LWS': 'Spin', 'SPIN': 'Spin', 'MIX': 'Mixed'}
ARM = {'RP': 'Right', 'LP': 'Left', 'OB': 'Right', 'LB': 'Right', 'SLA': 'Left', 'LWS': 'Left'}

rows = []
for r in csv.DictReader(open(bowlers_csv)):
    code, conf = BY_CRICINFO_ID.get(r['key_cricinfo']) or tags[r['name']]
    assert conf == 'y', f'unconfirmed tag: {r["name"]}'
    rows.append(dict(identifier=r['identifier'], name=r['name'], scorecard_names=r['scorecard_names'],
                     unique_name=r['unique_name'], key_cricinfo=r['key_cricinfo'],
                     type=TYPE[code], arm=ARM.get(code, ''), style=LABEL[code], code=code,
                     ipl_balls=r['balls'], ipl_wickets=r['wickets'],
                     first_season=r['first'], last_season=r['last'], teams=r['teams']))

with open(out_csv, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(len(rows), 'bowlers:', dict(Counter(r['style'] for r in rows)))
