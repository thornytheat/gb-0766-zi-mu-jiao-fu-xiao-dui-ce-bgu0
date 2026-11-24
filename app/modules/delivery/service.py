from .checks import verify

CODES = {'MISSING': '必填字段缺失', 'WIDTH': '列数不符', 'CUE_CONFLICT': '同轨同号内容冲突',
         'CUE_COPY': '相同字幕副本', 'TIME_LABEL': '时码格式无效', 'DROPPED_LABEL': '该帧号已跳过',
         'TIME_ORDER': '出点不晚于入点', 'OVERLAP': '同轨目标帧相交', 'GAP': '缺少切版记录',
         'SYNC_MISSING': '该卷缺同步点留待复核', 'SYNC_CONFLICT': '同卷同步点偏移冲突整卷复核',
         'HALF_SYNC': '跨卷仅半边对齐暂扣整句', 'SYNC_LABEL': '同步点时码或母带帧无效'}


def sync_evidence(stages):
    clock = stages['clock']
    if not clock.get('sync_active'):
        return None
    used = [point for entry in clock['reels'] if entry['status'] in ('ok', 'conflict')
            for point in entry['points']]
    return dict(points=used,
                reel_status=[{key: entry[key] for key in ('reel', 'status', 'offset')}
                             for entry in clock['reels']],
                withheld=stages['edits']['withheld'])


def signing(record):
    return dict(verified=True, certificate=verify(record), **record, reason_codes=CODES,
                sync_evidence=sync_evidence(record['stages']))
