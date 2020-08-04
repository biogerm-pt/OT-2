from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'V1 S14 Station A MagMax',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.4'
}

NUM_SAMPLES = 11    # Max number of samples - 64
SAMPLE_VOLUME = 242.5
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '2', '96-deepwell sample plate')
    tipracks1000 = [ctx.load_labware('opentrons_96_filtertiprack_1000ul', '1',
                                     '1000µl filter tiprack')]

    # load pipette
    p1000 = ctx.load_instrument(
        'p1000_single_gen2', 'right', tip_racks=tipracks1000)

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][p1000] = data['tips1000']
                else:
                    tip_log['count'][p1000] = 0
    else:
        tip_log['count'] = {p1000: 0}

    tip_log['tips'] = {
        p1000: [tip for rack in tipracks1000 for tip in rack.wells()]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [p1000]
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

    # pool samples
    for i in range(math.ceil(NUM_SAMPLES/2)):
        if NUM_SAMPLES % 2 != 0 and i == math.ceil(NUM_SAMPLES/2) - 1:
            pool_source_set = [dest_plate.wells()[NUM_SAMPLES]]
        else:
            pool_source_set = dest_plate.wells()[i*2:i*2+2]
        for s in pool_source_set:
            pick_up(p1000)
            p1000.transfer(SAMPLE_VOLUME, s, dest_plate.wells()[i+64], air_gap=20, mix_before=(1, 100); mix_after=(2, 75);
                           new_tip='never')
            p1000.air_gap(100)
            p1000.drop_tip()


    ctx.comment('Move deepwell plate (slot 2) to Station B for RNA \
extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {'tips1000': tip_log['count'][p1000]}
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
