import re
from fractions import Fraction
from app.problems import Rejection
from app.rational import show
from app.modules.source.reader import tabulate
from app.modules.clock.timecode import position

SYNC_FIELDS = ('reel', 'format', 'tape', 'master')
INTEGER = re.compile(r'[0-9]{1,12}')


def parse_points(csv_text):
    if not csv_text:
        return []
    rows, rejected, _, _, _ = tabulate(csv_text, {}, SYNC_FIELDS)
    if rejected:
        raise Rejection('SYNC_TABLE', '同步点表存在坏行')
    points = []
    for row in rows:
        try:
            tape_frame = position(row['tape'], row['format'])
            if not row['reel'].strip() or not INTEGER.fullmatch(row['master']):
                raise ValueError
            master = int(row['master'])
        except ValueError as exc:
            raise Rejection('SYNC_LABEL', f"同步点第 {row['line']} 行无效") from exc
        offset = Fraction(master) - tape_frame
        points.append(dict(reel=row['reel'], line=row['line'], format=row['format'], tape=row['tape'],
                           tape_frame=show(tape_frame), master=master, offset=show(offset)))
    points.sort(key=lambda point: (point['reel'], point['line']))
    return points


def evaluate(points, cues, edits):
    """同一时码跨卷各自落画：按卷核对；同卷偏移不一致整卷留待复核。"""
    by_reel = {}
    for point in points:
        by_reel.setdefault(point['reel'], []).append(point)
    offsets = {reel: {point['offset'] for point in bucket} for reel, bucket in by_reel.items()}
    retained = {edit['reel'] for edit in edits if edit['kind'] == 'KEEP'}
    cue_reels = {cue['reel'] for cue in cues}
    reels = []
    isolated = []
    for reel in sorted(cue_reels | set(by_reel)):
        bucket = by_reel.get(reel, [])
        if not bucket:
            if reel in retained:
                status, code = 'missing', 'SYNC_MISSING'
            else:
                # 切版未保留整卷画面：缺同步点不记作待核
                status, code = 'exempt', None
        elif len(offsets[reel]) > 1:
            status, code = 'conflict', 'SYNC_CONFLICT'
        else:
            status, code = 'ok', None
        entry = dict(reel=reel, status=status,
                     offset=show(next(iter(offsets[reel]))) if status in ('ok', 'conflict') else None,
                     points=bucket)
        reels.append(entry)
        if code:
            for cue in cues:
                if cue['reel'] == reel:
                    isolated.append(dict(cue, code=code))
    held = {(row['track'], row['cue_id']) for row in isolated}
    return dict(reels=reels, isolated=isolated, held=held,
                counts=dict(ok=sum(r['status'] == 'ok' for r in reels),
                            conflict=sum(r['status'] == 'conflict' for r in reels),
                            missing=sum(r['status'] == 'missing' for r in reels),
                            exempt=sum(r['status'] == 'exempt' for r in reels)))

def reel_offset(reels):
    return {entry['reel']: Fraction(entry['offset']) for entry in reels if entry['offset'] is not None}
