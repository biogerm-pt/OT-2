import opentrons.execute
protocol = opentrons.execute.get_protocol_api('2.5')
protocol.home()
#protocol.set_rail_lights (True)


s_racks = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '11')

d_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '9')
  
tips300 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '8')

p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[tips300])

    # code
    
p300.transfer(100, s_racks.wells ('A1'), d_plate.wells('A1'), air_gap=20,mix_before=(2, 200))

protocol.home()