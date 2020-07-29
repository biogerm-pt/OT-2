
#test

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

NUM_SAMPLES = 32
SAMPLE_VOLUME = 100
TIP_TRACK = False

    
def run(ctx: protocol_api.ProtocolContext):

    # load labware

    s_racks = [
        ctx.load_labware(
            'opentrons_15_tuberack_falcon_15ml_conical', '4')
    ]
    d_plate = ctx.load_labware(
        'nest_96_wellplate_200ul_flat', '1', '96-wellplate sample plate')
  
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '5')]
  

    # load pipette

    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)
    
    

   

    # transfer sample
    

    p300.transfer(SAMPLE_VOLUME, s_racks.wells () ['A1'], d_plate.columns()['5'], air_gap=20,
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
