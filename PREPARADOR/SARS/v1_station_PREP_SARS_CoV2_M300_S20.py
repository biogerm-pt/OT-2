from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'V1 Station Prep SARS CoV2 MagMax',
    'author': 'Ricmag <ricmags@sapo.pt>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.5'
}

NUM_SAMPLES = 10
BB_VOLUME = 412,5
ICPK_VOlUME = 15
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    ic_pk = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '9',
        'chilled tubeblock for internal control and proteinase K (strip 1)').wells()[0]

    bb = ctx.load_labware(
        'nest_12_reservoir_15ml', '8', 'reagent reservoir Binding Buffer')
    binding_buffer = bb.wells()[:2]    
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '11', '96-deepwell sample plate')


    # load tips
  
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '5',
                                    '200µl filter tiprack')]
    tips20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '6',
                                    '20µl filter tiprack')]

    # load pipette

    m300 = ctx.load_instrument('p300_multi_gen2', 'left', tip_racks=tips300)
    s20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)
  
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    s20.flow_rate.aspirate = 50
    s20.flow_rate.dispense = 100
    s20.flow_rate.blow_out = 300

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
                if 'tips20' in data:
                    tip_log['count'][s20] = data['tips20']
                else:
                    tip_log['count'][s20] = 0
    else:
        tip_log['count'] = {m300: 0, s20: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tips300 for tip in rack.wells()],
        s20: [tip for rack in tips20 for tip in rack.rows()[0]]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [m300, s20]
    }
    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \ resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1


    # setup samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    sources = bb.wells()[:2]
    dests_single = dest_plate.wells()[:NUM_SAMPLES]

 # transfer internal control + proteinase K
    for d in dests_single:
        pick_up(s20)
        s20.transfer(ICPK_VOlUME, ic_pk.bottom(2), d.bottom(10), air_gap=5,
                     new_tip='never')
        s20.air_gap(5)
        s20.drop_tip()    

    # transfer binding buffer
    for d in dests_single:
        pick_up(s20)
        m300.transfer(BB_VOLUME, sources, d, air_gap=5,
                     new_tip='never')
        m300.air_gap(5)
        m300.drop_tip()    

  

    

    ctx.comment('Terminado.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips300': tip_log['count'][m300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
