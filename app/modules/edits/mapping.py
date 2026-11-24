from bisect import bisect_right
from fractions import Fraction
from math import ceil
from app.modules.clock.timecode import RATIO
from app.rational import show


def map_cues(cues, edit_list, held_sentences=frozenset()):
    index = {}
    for reel in {edit['reel'] for edit in edit_list}:
        reel_edits = [edit for edit in edit_list if edit['reel'] == reel]
        index[reel] = (reel_edits, [edit['end'] for edit in reel_edits])
    fragments = []
    for cue in cues:
        reel_edits, endpoints = index.get(cue['reel'], ([], []))
        shift = Fraction(cue.get('offset', 0))
        # 切版区间按各卷带位帧表述；偏移只用于记录母带帧，不改变卷内切段几何
        cursor, end = Fraction(cue['start']), Fraction(cue['end'])
        for edit in reel_edits[bisect_right(endpoints, cursor):]:
            if edit['start'] >= end:
                break
            left, right = max(cursor, edit['start']), min(end, edit['end'])
            if cursor < left:
                fragments.append(fragment(cue, cursor, left, None, shift))
            fragments.append(fragment(cue, left, right, edit, shift))
            cursor = right
        if cursor < end:
            fragments.append(fragment(cue, cursor, end, None, shift))
    withheld = set()
    for row in fragments:
        if row['kind'] == 'KEEP' and (row['track'], row['cue_id']) in held_sentences:
            row['code'] = 'HALF_SYNC'
            withheld.add((row['track'], row['cue_id']))
    counts = {kind: sum(row['kind'] == kind for row in fragments) for kind in ('KEEP', 'REMOVE', 'GAP')}
    counts['withheld'] = sum(row.get('code') == 'HALF_SYNC' for row in fragments)
    return dict(rows=fragments, cuts=edit_list, counts=counts,
                withheld=[list(key) for key in sorted(withheld)])


def fragment(cue, start, end, edit, shift):
    kind = edit['kind'] if edit else 'GAP'
    result = dict(cue_id=cue['cue_id'], track=cue['track'], line=cue['line'], text=cue['text'],
                  reel=cue['reel'], start=show(start), end=show(end),
                  master_start=show(start + shift), master_end=show(end + shift),
                  kind=kind, cut=edit['cut'] if edit else None, cut_line=edit['line'] if edit else None)
    if kind == 'KEEP':
        # 卷内目标坐标由切版目标锚点与带位几何决定；母带帧随段保留用于覆盖对账
        left = edit['target'] + (start - edit['start']) * RATIO
        right = edit['target'] + (end - edit['start']) * RATIO
        result.update(target_start=show(left), target_end=show(right), frame_in=ceil(left), frame_out=ceil(right))
    return result
