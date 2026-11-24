from fractions import Fraction
from app.rational import show
from .coverage import union_length


def balance(timing_or_cues, mapped, overlaps, rejected):
    if isinstance(timing_or_cues, dict):
        timing = timing_or_cues
        cues = timing['rows']
        exempt = timing.get('exempt', [])
        reels = timing.get('reels', [])
    else:
        timing = None
        cues = timing_or_cues
        exempt, reels = [], []
    total = dict(original=Fraction(0), delivered=Fraction(0), removed=Fraction(0), pending=Fraction(0),
                 signable=Fraction(0), withheld=Fraction(0))
    rows = []
    tracks = sorted({row['track'] for row in cues} | {row['track'] for row in exempt})
    for track in tracks:
        pieces = [row for row in mapped['rows'] if row['track'] == track] if isinstance(mapped, dict) \
            else [row for row in mapped if row['track'] == track]
        exact = dict(original=union_length([row for row in cues if row['track'] == track]))
        for name, kind in [('delivered', 'KEEP'), ('removed', 'REMOVE'), ('pending', 'GAP')]:
            exact[name] = union_length([row for row in pieces if row['kind'] == kind])
        kept = [row for row in pieces if row['kind'] == 'KEEP']
        exact['signable'] = union_length([row for row in kept if row.get('code') != 'HALF_SYNC'])
        exact['withheld'] = union_length([row for row in kept if row.get('code') == 'HALF_SYNC'])
        for name, number in exact.items():
            total[name] += number
        rows.append(dict(track=track, **{name: show(value) for name, value in exact.items()}))
    gap = total['original'] - total['delivered'] - total['removed'] - total['pending']
    counts = dict(**{name: show(value) for name, value in total.items()},
                  rejected_unmeasurable=rejected, overlap_target_frames=overlaps,
                  exempt_cues=len(exempt),
                  exempt_reels=sum(entry['status'] == 'exempt' for entry in reels))
    return dict(rows=rows, counts=counts, balanced=gap == 0, difference=show(gap),
                signable_balanced=total['delivered'] == total['signable'] + total['withheld'])
