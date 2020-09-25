from opentrons import protocol_api

metadata = {'apiLevel': '2.5'}

NUM_SAMPLES = 32
SAMPLE_VOLUME = 200


def run(protocol: protocol_api.ProtocolContext):
    sou = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 4)
    dest = protocol.load_labware('opentrons_96_filtertiprack_200ul', 3)
    tiprack_1 = protocol.load_labware('opentrons_96_filtertiprack_200ul', 2)
    p300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks=[tiprack_1])
    dests_single = dest.wells()[:NUM_SAMPLES]

   
    p300.pick_up_tip (tiprack_1.wells()[0])
    p300.drop_tip (dest.wells()[0])  

