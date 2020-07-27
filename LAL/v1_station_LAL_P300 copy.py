from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'V1 Station A LAL P300',
    'author': 'Ricmag <ricmags@sapo.pt>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 10
SAMPLE_VOLUME = 100
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware

    source_racks = [
        ctx.load_labware(
            'opentrons_15_tuberack_falcon_15ml_conical', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['11', '10', '7', '4', '5', '6', '3'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_200ul_flat', '9', '96-wellplate sample plate')
  
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '8')]
  

    # load pipette

    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)
    
    

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests_single = dest_plate.wells()[:NUM_SAMPLES]

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips300' in data:
                    tip_log['count'][p300] = data['tips300']
                else:
                    tip_log['count'][p300] = 0

    else:
        tip_log['count'] = {p300: 0}#, m20: 0}

    tip_log['tips'] = {
        p300: [tip for rack in tips300 for tip in rack.wells()]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p300]
    }

    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1

    # transfer two controls
    # **Incluir o labware (suporte de eppendorf)
    # definir local branco
    # if TRUE reta de calibração

    # transfer sample
    for s, d in zip(sources, dests_single):
        pick_up(p300)
        p300.transfer(SAMPLE_VOLUME, s.bottom(5), d.bottom(5), air_gap=20,
                      mix_before=(2, 200), new_tip='never')
        p300.air_gap(20)
        p300.drop_tip()

    

    ctx.comment('Terminado.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips300': tip_log['count'][p300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
