from .problems import Rejection
from .settings import SAMPLE_ROOT

SAMPLES = ('dirty', 'clean', 'taped')


def example(name):
    if name not in SAMPLES:
        raise Rejection('NO_SAMPLE', '找不到交付样例', 404)
    root = SAMPLE_ROOT / name
    fields = ('cues', 'cuts') + (('syncs',) if (root / 'syncs.csv').exists() else ())
    return {field: (root / f'{field}.csv').read_bytes().decode() for field in fields}


def material(body):
    if isinstance(body, dict) and set(body) == {'sample'}:
        return example(body['sample'])
    if isinstance(body, dict) and {'cues', 'cuts'} <= set(body) <= {'cues', 'cuts', 'syncs'} \
            and all(isinstance(text, str) for text in body.values()):
        return body
    raise Rejection('PAYLOAD', '提交字幕和切版 CSV')
