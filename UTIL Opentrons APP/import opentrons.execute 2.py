import opentrons.execute
protocol = opentrons.execute.get_protocol_api('2.5')
protocol.home()
#protocol.set_rail_lights (True)


NUM_SAMPLES = 32
SAMPLE_VOLUME = 100
TIP_TRACK = False

s_racks = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '11')

d_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '9')
  
tips300 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '8')

p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[tips300])

    # code
    
dests_single = d_plate.wells()[:NUM_SAMPLES]


p300.transfer(100, s_racks.wells ('A1'), dests_single, air_gap=20,mix_before=(2, 200))

protocol.home()




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

NUM_SAMPLES = 10
SAMPLE_VOLUME = 100
TIP_TRACK = False


s_racks = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '11')

d_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '9')
  
tips300 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '8')

p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[tips300])

    # code
    
dests_single = d_plate.wells()[:NUM_SAMPLES]


p300.transfer(100, s_racks.wells ('A1'), dests_single, air_gap=20,mix_before=(2, 200))

protocol.home()


import opentrons.execute
protocol = opentrons.execute.get_protocol_api('2.5')
protocol.home()
#protocol.set_rail_lights (True)


NUM_SAMPLES = 32
SAMPLE_VOLUME = 100
TIP_TRACK = False

s_racks = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '11')

d_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '9')
  
tips300 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '8')

p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[tips300])

    # code
    
dests_single = d_plate.wells()[:NUM_SAMPLES]


p300.transfer(100, s_racks.wells ('A1'), dests_single, air_gap=20,mix_before=(2, 200))

    

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
