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
SAMPLE_VOLUME = 100
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    ic_pk = ctx.load_labware(
        'opentrons_96_aluminumblock_generic_pcr_strip_200ul', '9',
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
    m20 = ctx.load_instrument('p20_multi_gen2', 'right', tip_racks=tips20)
  
    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    m20.flow_rate.aspirate = 50
    m20.flow_rate.dispense = 100
    m20.flow_rate.blow_out = 300

    # setup samples
    num_cols = math.ceil(NUM_SAMPLES/8)
    sources = bb.wells()[:2]
    dests_multi = dest_plate.rows()[0][:num_cols]

 # transfer internal control + proteinase K
    for d in dests_multi:
        pick_up(m20)
        m20.transfer(15, ic_pk.bottom(2), d.bottom(10), air_gap=5,
                     new_tip='never')
        m20.air_gap(5)
        m20.drop_tip()    

    # transfer binding buffer
    for d in dests_multi:
        pick_up(m20)
        m20.transfer(15, sources.bottom(2), d.bottom(10), air_gap=5,
                     new_tip='never')
        m20.air_gap(5)
        m20.drop_tip()    

  

    

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
