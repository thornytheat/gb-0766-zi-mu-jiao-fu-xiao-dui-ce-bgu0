from app.digests import digest, encode, fingerprints
from app.problems import Rejection


def verify(record):
    stamp = record['manifest']
    if (fingerprints(record['original']) != stamp['input_sha256'] or
            digest(encode(record['stages'])) != stamp['result_sha256'] or
            not record['stages']['source']['counts']['balanced'] or
            not record['stages']['balance']['balanced']):
        raise Rejection('INVALID_EVIDENCE', '证据散列或覆盖勾稽不符', 409)
    if not record['stages']['balance'].get('signable_balanced'):
        raise Rejection('HALF_SENTENCE', '跨卷半句不得进入签发包', 409)
    if record['stages']['clock'].get('sync_active'):
        _verify_sync(record['stages'])
    return stamp


def _verify_sync(stages):
    used = stages.get('sync_evidence')
    if not used:
        raise Rejection('SYNC_EVIDENCE', '签发包缺少同步点证据', 409)
    points = {(point['reel'], point['line']) for entry in stages['clock']['reels'] for point in entry['points']}
    recorded = {(point['reel'], point['line']) for point in used['points']}
    if not recorded or not recorded <= points:
        raise Rejection('SYNC_EVIDENCE', '签发包同步点无法回溯', 409)
    if any(row.get('code') == 'HALF_SYNC' for row in stages['edits']['rows']):
        raise Rejection('HALF_SENTENCE', '跨卷半句不得进入签发包', 409)
    sentences = stages['source']['sentences']
    kept_reels = {}
    for row in stages['edits']['rows']:
        if row['kind'] == 'KEEP':
            kept_reels.setdefault('|'.join((row['track'], row['cue_id'])), set()).add(row['reel'])
    for key, reels in kept_reels.items():
        sentence = set(sentences.get(key, ()))
        if reels != sentence:
            raise Rejection('HALF_SENTENCE', '跨卷半句不得进入签发包', 409)
