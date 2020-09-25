from opentrons import protocol_api

metadata = {'apiLevel': '2.5'}

NUM_SAMPLES = 32
SAMPLE_VOLUME = 200


def run(protocol: protocol_api.ProtocolContext):
    sou = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', 4)
    dest = protocol.load_labware('nest_96_wellplate_200ul_flat', 1)
    tiprack_1 = protocol.load_labware('opentrons_96_filtertiprack_200ul', 5)
    p300 = protocol.load_instrument('p300_single', 'left', tip_racks=[tiprack_1])
    dests_single = dest.wells()[:NUM_SAMPLES]

    p300.transfer(100, sou.wells_by_name () ['A1'], dests_single )

