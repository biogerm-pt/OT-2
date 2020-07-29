import opentrons.execute
protocol = opentrons.execute.get_protocol_api('2.5')
protocol.home()
#protocol.set_rail_lights (True)

NUM_SAMPLES = 32
SAMPLE_VOLUME = 100
TIP_TRACK = False

s_racks = protocol.load_labware('opentrons_15_tuberack_falcon_15ml_conical', '10')

d_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', '11')
  
tips300 = protocol.load_labware('opentrons_96_filtertiprack_200ul', '8')

p300 = protocol.load_instrument('p300_single_gen2', 'left', tip_racks=[tips300])

    # code
    
#p300.transfer(100, s_racks.wells ('A1'), d_plate.wells('A1'), air_gap=20,mix_before=(2, 200))

 # setup samples
sources = s_racks.wells ('A1')
dests_single = d_plate.wells()[:NUM_SAMPLES]
    
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


for s, d in zip(sources, dests_single):
        pick_up(p300)
        p300.transfer(SAMPLE_VOLUME, s.bottom(5), d.bottom(5), air_gap=20,mix_before=(2, 200))
        p300.air_gap(20)
        p300.drop_tip()



protocol.home()