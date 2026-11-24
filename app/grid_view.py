HEADERS = {
    'source': ('line', 'cue_id', 'reel', 'format', 'in', 'out', 'code', 'text'),
    'clock': ('line', 'cue_id', 'reel', 'in', 'out', 'start', 'end', 'master_start', 'master_end',
              'offset', 'nominal_start', 'code'),
    'edits': ('line', 'cue_id', 'reel', 'start', 'end', 'cut', 'kind', 'frame_in', 'frame_out', 'code'),
    'overlaps': ('frame_in', 'frame_out', 'frames', 'track', 'cues', 'lines', 'code'),
    'balance': ('track', 'original', 'delivered', 'signable', 'withheld', 'removed', 'pending'),
    'runs': ('id', 'version', 'created_at', 'elapsed_us'),
    'delivery': ('field', 'hash'),
}
LABELS = {'line': '原行', 'cue_id': '字幕号', 'reel': '卷', 'format': '格式', 'in': '原入点', 'out': '原出点',
          'code': '原因', 'text': '字幕文本', 'start': '源入帧', 'end': '源出帧', 'master_start': '母带入帧',
          'master_end': '母带出帧', 'offset': '同步偏移', 'nominal_start': '折算入帧', 'cut': '切段',
          'kind': '分段判定', 'frame_in': '目标入帧', 'frame_out': '目标出帧', 'frames': '重叠帧',
          'track': '轨道', 'cues': '字幕号', 'lines': '原行组', 'original': '原覆盖', 'delivered': '交付覆盖',
          'signable': '可签发', 'withheld': '同步暂扣', 'removed': '剪辑移除', 'pending': '缺段待证',
          'id': '归档档号', 'version': '规则版本', 'created_at': '生成 UTC', 'elapsed_us': '耗时 μs',
          'field': '原件', 'hash': 'SHA-256'}


def cells(stages, sheet, archive, stamp):
    if sheet == 'runs':
        return archive.inventory()
    if sheet == 'delivery':
        rows = [dict(field=key, hash=value) for key, value in stamp['input_sha256'].items()] if stamp else []
        evidence = (stages.get('sync_evidence') or {}) if stamp else {}
        for point in evidence.get('points', []):
            rows.append(dict(field=f"同步点 {point['reel']} 原行{point['line']}",
                             hash=f"{point['tape']} → 母带 {point['master']}（偏移 {point['offset']}）"))
        return rows
    view = stages[sheet]
    return view.get('isolated', []) + view.get('copies', []) + view['rows']
