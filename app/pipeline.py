from .modules.delivery.service import sync_evidence
from .modules.source.service import receive
from .modules.clock.service import validate
from .modules.edits.contract import timeline
from .modules.edits.mapping import map_cues
from .modules.overlaps.service import locate
from .modules.balance.service import balance


def inspect(material, until=None):
    source = receive(material['cues'])
    if until == 'source':
        return source
    sync_text = material.get('syncs', '')
    needs_cuts = bool(sync_text) or until in (None, 'edits', 'overlaps', 'balance')
    edits = timeline(material['cuts']) if needs_cuts else []
    timing = validate(source['rows'], sync_text, edits)
    if until == 'clock':
        return timing
    cuts = map_cues(timing['rows'], edits, set(timing.get('held', ())))
    if until == 'edits':
        return cuts
    clashes = locate(cuts['rows'])
    if until == 'overlaps':
        return clashes
    check = balance(timing, cuts, clashes['counts']['overlap_frames'],
                    len(source['isolated']) + len(timing['isolated']))
    if until == 'balance':
        return check
    stages = dict(source=source, clock=timing, edits=cuts, overlaps=clashes, balance=check)
    stages['sync_evidence'] = sync_evidence(stages)
    return stages
