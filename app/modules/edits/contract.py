import re
from app.problems import Rejection
from app.modules.clock.timecode import RATIO
from app.modules.source.reader import tabulate
from app.modules.source.service import DEFAULT_REEL

CUT_FIELDS = ('cut', 'start', 'end', 'target', 'kind')


def timeline(csv_text):
    rows, rejected, _, _, _ = tabulate(csv_text, {}, CUT_FIELDS, ('reel',))
    if rejected or not rows:
        raise Rejection('CUTS', '切版表存在坏行或为空')
    reeled = 'reel' in rows[0]
    edits = []
    labels = set()
    for row in rows:
        cut = row['cut']
        if not cut or cut in labels or row['kind'] not in ('KEEP', 'REMOVE'):
            raise Rejection('CUT_KIND', f"切版第 {row['line']} 行定义无效")
        labels.add(cut)
        kept = row['kind'] == 'KEEP'
        try:
            start, end = [frame_integer(row[k]) for k in ('start', 'end')]
            target = frame_integer(row['target']) if kept else None
            if start >= end or (not kept and row['target'] != ''):
                raise ValueError
        except ValueError as exc:
            raise Rejection('CUT_RANGE', f"切版第 {row['line']} 行定义无效") from exc
        if not reeled or not row.get('reel'):
            row['reel'] = DEFAULT_REEL
        edits.append(dict(row, start=start, end=end, target=target))
    edits.sort(key=lambda row: (row['reel'], row['start']))
    if any(left['reel'] == right['reel'] and left['end'] > right['start']
           for left, right in zip(edits, edits[1:])):
        raise Rejection('CUT_OVERLAP', '同源切版区间互相覆盖')
    target = sorted((row['reel'], row['target'], row['target'] + (row['end'] - row['start']) * RATIO)
                    for row in edits if row['kind'] == 'KEEP')
    if any(left[0] == right[0] and left[2] > right[1] for left, right in zip(target, target[1:])):
        raise Rejection('TARGET_OVERLAP', '目标切版区间互相覆盖')
    return edits


def frame_integer(value):
    if not re.fullmatch(r'[0-9]{1,12}', value):
        raise ValueError('invalid frame')
    return int(value)
