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

#pooling com pipeta de m300 da Coluna 1 e 2 para Coluna 9

NUM_SAMPLES = 64
SAMPLE_VOLUME = 100
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '2', '96-deepwell sample plate')
    tipracks300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '1',
                                    '200µl filter tiprack')]

    # load pipette
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks300)

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][m300] = data['tips1000']
                else:
                    tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {m300: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tipracks300 for tip in rack.rows()[0]]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [m300]
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
    num_cols = math.ceil(NUM_SAMPLES/8)
    for i in range(math.ceil(num_cols/2)):
        if num_cols % 2 != 0 and i == math.ceil(num_cols/2) - 1:
            pool_source_set = [dest_plate.rows()[0][num_cols]]
            vol = SAMPLE_VOLUME*2
        else:
            pool_source_set = dest_plate.rows()[0][i*2:i*2+2]
            vol = SAMPLE_VOLUME
        for s in pool_source_set:
            pick_up(m300)
            m300.transfer(vol, s, dest_plate.rows()[0][i+8], air_gap=20,
                          new_tip='never')
            m300.air_gap(20)
            m300.drop_tip()

    ctx.comment('Move deepwell plate (slot 2) to Station B for RNA \
extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {'tips1000': tip_log['count'][m300]}
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
