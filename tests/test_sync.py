import pytest
from app.material import example
from app.pipeline import inspect
from app.modules.clock.sync import evaluate, parse_points
from app.modules.delivery.service import signing
from app.modules.runs.files import CutArchive
from app.modules.runs.service import record
from app.problems import Rejection

TAPED = example('taped')


def test_same_timecode_lands_on_each_reels_master_frame():
    # 规则一/规则二：同一带位时码 100 在 R1、R2 各自落到本卷母带帧
    stages = inspect(TAPED)
    rows = {(row['reel'], row['cue_id']): row for row in stages['clock']['rows']}
    assert rows[('R1', 'C301')]['master_start'] == '1900'
    assert rows[('R2', 'C302')]['master_start'] == '1900'
    assert rows[('R1', 'C301')]['start'] == rows[('R2', 'C302')]['start'] == '100'
    r1, r2 = stages['edits']['rows'][0], stages['edits']['rows'][1]
    assert (r1['frame_in'], r2['frame_in']) == (81, 581)


def test_conflicting_offsets_hold_whole_reel():
    # 规则三：R3 两个同步点给出 2900 与 3000 两个偏移，整卷留待复核
    stages = inspect(TAPED)
    reels = {entry['reel']: entry for entry in stages['clock']['reels']}
    assert reels['R3']['status'] == 'conflict'
    assert {row['cue_id'] for row in stages['clock']['isolated'] if row['code'] == 'SYNC_CONFLICT'} == {'C303'}


def test_cross_reel_half_aligned_withholds_full_sentence():
    # 规则四：C303 跨 R2/R3，R3 待核，两个半边的 KEEP 段都不得只放半句
    stages = inspect(TAPED)
    halves = [row for row in stages['edits']['rows'] if row['cue_id'] == 'C303']
    assert len(halves) == 2 and all(row['code'] == 'HALF_SYNC' for row in halves)
    counts = stages['balance']['counts']
    assert counts['withheld'] == '60' and counts['signable'] == '40'


def test_reel_without_kept_picture_is_exempt_not_pending():
    # 规则五：R4 整卷 REMOVE，缺同步点不记作待核
    stages = inspect(TAPED)
    reels = {entry['reel']: entry for entry in stages['clock']['reels']}
    assert reels['R4']['status'] == 'exempt'
    assert all(row['code'] != 'SYNC_MISSING' for row in stages['clock']['isolated'])
    assert [(row['cue_id'], row['reel']) for row in stages['clock']['exempt']] == [('C304', 'R4')]
    assert stages['balance']['counts']['exempt_reels'] == 1


def test_missing_sync_on_kept_reel_is_pending():
    syncs = '\n'.join(TAPED['syncs'].splitlines()[:5]) + '\n'  # 去掉 R3 全部同步点
    stages = inspect(dict(TAPED, syncs=syncs))
    reels = {entry['reel']: entry for entry in stages['clock']['reels']}
    assert reels['R3']['status'] == 'missing'
    assert any(row['code'] == 'SYNC_MISSING' for row in stages['clock']['isolated'])


def test_downloaded_package_carries_used_sync_points(tmp_path):
    # 规则六：签发包可回溯用过的同步点
    store = CutArchive(tmp_path)
    saved = record(store, TAPED)
    with pytest.raises(Rejection, match='半句'):
        signing(store.read(saved['id']))
    late = dict(TAPED)
    late['syncs'] = TAPED['syncs'].replace('R3,FRAME,200,3200', 'R3,FRAME,200,3100') \
        + 'R3,FRAME,300,3200\n'
    fixed = record(store, late)
    pack = signing(store.read(fixed['id']))
    points = {(point['reel'], point['line']) for point in pack['sync_evidence']['points']}
    assert points == {('R1', 2), ('R1', 3), ('R2', 4), ('R2', 5), ('R3', 6), ('R3', 7), ('R3', 8)}
    assert {entry['reel']: entry['status'] for entry in pack['sync_evidence']['reel_status']} == \
        {'R1': 'ok', 'R2': 'ok', 'R3': 'ok', 'R4': 'exempt'}


def test_late_sync_records_trigger_recalculation(tmp_path):
    # 规则六续：晚到记录补齐后重算，新归档结果可签发且覆盖守恒
    store = CutArchive(tmp_path)
    first = record(store, TAPED)
    late = dict(TAPED)
    late['syncs'] = TAPED['syncs'].replace('R3,FRAME,200,3200', 'R3,FRAME,200,3100') \
        + 'R3,FRAME,300,3200\n'
    second = record(store, late)
    assert first['id'] != second['id'] and second['reused'] is False
    pack = signing(store.read(second['id']))
    assert pack['stages']['balance']['counts']['withheld'] == '0'
    assert all(row.get('code') != 'HALF_SYNC' for row in pack['stages']['edits']['rows'])


def test_sync_offsets_are_exact_rational():
    points = parse_points('reel,format,tape,master\nR1,DF,00:01:00;02,1802\n')
    assert points[0]['offset'] == '2'
    points = parse_points('reel,format,tape,master\nR1,VTT,00:30.030,901\n')
    assert points[0]['offset'] == '1'


def test_bad_sync_table_rejected():
    with pytest.raises(Rejection) as error:
        parse_points('reel,format,tape,master\nR1,DF,00:01:00;00,1800\n')
    assert error.value.code == 'SYNC_LABEL'
    with pytest.raises(Rejection) as error:
        inspect(dict(TAPED, syncs='reel,format,tape,master\nR1,FRAME,100,x\n'))
    assert error.value.code == 'SYNC_LABEL'


def test_sync_conflict_takes_precedence_over_missing():
    cues = [dict(cue_id='C1', track='t', reel='R9', line=2, start='10', end='20')]
    edits = [dict(reel='R9', kind='KEEP')]
    points = parse_points('reel,format,tape,master\nR9,FRAME,10,100\nR9,FRAME,20,220\n')
    result = evaluate(points, cues, edits)
    assert result['reels'][0]['status'] == 'conflict'


def test_malformed_sync_width_rejected():
    with pytest.raises(Rejection) as error:
        parse_points('reel,format,tape,master\nR9,FRAME,10,100,EXTRA\n')
    assert error.value.code == 'SYNC_TABLE'


def test_preview_accepts_partial_sync_without_failure():
    # 预映等不齐所有卷：只出待核结论，不抛错
    stages = inspect(dict(TAPED, syncs='reel,format,tape,master\nR1,FRAME,100,1900\n'))
    status = {entry['reel']: entry['status'] for entry in stages['clock']['reels']}
    assert status == {'R1': 'ok', 'R2': 'missing', 'R3': 'missing', 'R4': 'exempt'}
    assert all(row['kind'] in ('KEEP', 'REMOVE', 'GAP') for row in stages['edits']['rows'])
