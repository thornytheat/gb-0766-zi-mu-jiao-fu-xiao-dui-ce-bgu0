from fractions import Fraction
from app.rational import show
from .timecode import RATIO, position
from .sync import evaluate, parse_points, reel_offset


def validate(cues, sync_text='', edits=()):
    valid, isolated = [], []
    for cue in cues:
        try:
            start, end = [position(cue[k], cue['format']) for k in ('in', 'out')]
            if start >= end:
                raise ValueError('TIME_ORDER')
        except ValueError as error:
            isolated.append(dict(cue, code=str(error)))
            continue
        valid.append(dict(cue, start=show(start), end=show(end),
                          nominal_start=show(start * RATIO), nominal_end=show(end * RATIO)))

    sync_active = bool(sync_text)
    points = parse_points(sync_text) if sync_active else []
    sync = evaluate(points, cues, edits) if sync_active else None
    if sync is not None:
        offsets = reel_offset(sync['reels'])
        aligned, exempt = [], []
        exempt_reels = {entry['reel'] for entry in sync['reels'] if entry['status'] == 'exempt'}
        for cue in valid:
            if cue['reel'] in exempt_reels:
                exempt.append(cue)
                continue
            shift = offsets.get(cue['reel'])
            if shift is None:
                continue
            cue['offset'] = show(shift)
            cue['master_start'] = show(Fraction(cue['start']) + shift)
            cue['master_end'] = show(Fraction(cue['end']) + shift)
            aligned.append(cue)
        isolated.extend(sync['isolated'])
        isolated.sort(key=lambda row: (row['line'], row.get('reel', '')))
        rows = aligned
        result = dict(rows=rows, isolated=isolated, exempt=exempt, held=list(sync['held']),
                      counts=dict(valid=len(rows), isolated=len(isolated)),
                      reels=sync['reels'], sync_active=True,
                      counts_detail=dict(timed=len(valid), exempt_cues=len(exempt),
                                         held=len(sync['isolated']), **sync['counts']))
    else:
        for cue in valid:
            cue['offset'] = '0'
            cue['master_start'] = cue['start']
            cue['master_end'] = cue['end']
        result = dict(rows=valid, isolated=isolated,
                      counts=dict(valid=len(valid), isolated=len(isolated)),
                      reels=[], sync_active=False)
    return result
