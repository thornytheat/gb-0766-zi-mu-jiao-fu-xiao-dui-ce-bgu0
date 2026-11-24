from app.material import example
from app.modules.balance.service import balance
from app.modules.balance.coverage import union_length
from app.pipeline import inspect


def test_dirty_cover(dirty):
    counts = dirty['balance']['counts']
    assert {key: counts[key] for key in
            ('original', 'delivered', 'removed', 'pending', 'rejected_unmeasurable', 'overlap_target_frames')
            } == dict(original='1140', delivered='740', removed='200', pending='200',
                      rejected_unmeasurable=5, overlap_target_frames=65)
    assert (counts['signable'], counts['withheld'], counts['exempt_cues']) == ('740', '0', 0)


def test_clean_cover():
    assert inspect(example('clean'))['balance']['rows'][1]['original'] == '100'


def test_conserves(dirty):
    assert dirty['balance']['balanced'] and dirty['balance']['difference'] == '0'


def test_missing_piece_detected(dirty):
    output = balance(dirty['clock']['rows'], [p for p in dirty['edits']['rows'] if p['kind'] != 'GAP'], 0, 0)
    assert output['difference'] == '200' and not output['balanced']


def test_fraction_union():
    assert str(union_length([dict(start='1/3',end='5/3'),dict(start='2/3',end='6/3')])) == '5/3'


def test_no_timing_evidence():
    output = balance([], [], 0, 3)
    assert output['counts']['original'] == '0' and output['counts']['rejected_unmeasurable'] == 3
