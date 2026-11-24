from collections import defaultdict
from .account import account
from .reader import tabulate

FIELDS = ('cue_id', 'track', 'format', 'in', 'out', 'text')
OPTIONAL = ('reel',)
DEFAULT_REEL = 'R1'
MISSING = {'', '-', 'N/A', 'NULL', '未知'}
ALIASES = {'legacy_id': 'cue_id', 'time_in': 'in', 'time_out': 'out'}


def receive(text):
    rows, isolated, headings, blanks, data_lines = tabulate(text, ALIASES, FIELDS, OPTIONAL)
    reeled = 'reel' in rows[0] if rows else False
    groups = defaultdict(list)
    for row in rows:
        if 'reel' not in row or not row['reel']:
            row['reel'] = DEFAULT_REEL
        if any(row[key] in MISSING for key in FIELDS):
            isolated.append(dict(row, code='MISSING'))
        else:
            groups[row['track'], row['cue_id'], row['reel']].append(row)
    cues, copies = [], []
    for group in groups.values():
        if len({tuple(row[key] for key in FIELDS) for row in group}) > 1:
            isolated.extend(dict(row, code='CUE_CONFLICT') for row in group)
        else:
            cues.append(group[0])
            copies.extend(dict(row, code='CUE_COPY') for row in group[1:])
    cues.sort(key=lambda row: (row['line'], row['reel']))
    linkage = defaultdict(set)
    for row in cues:
        linkage[row['track'], row['cue_id']].add(row['reel'])
    sentences = {'|'.join(key): sorted(reels) for key, reels in linkage.items()}
    return dict(rows=cues, isolated=sorted(isolated, key=lambda row: row['line']), copies=copies,
                reeled=reeled, sentences=sentences,
                counts=account(cues, isolated, copies, headings, blanks, data_lines))
