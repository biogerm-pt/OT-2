from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'V3 S14 Station A MagMax',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.0'
}

NUM_SAMPLES = 96
TUBE50_VOlUME = 20

BB_VOLUME = 350
MIX_REPETITIONS = 3
MIX_VOLUME = 300
ICPK_VOlUME = 15
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):

    # load labware
    ic_pk = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_snapcap', '9',
        'chilled tubeblock for internal control and proteinase K (strip 1)').wells()[0]
    source_racks = [
        ctx.load_labware(
            'opentrons_24_tuberack_eppendorf_2ml_safelock_snapcap', slot,
            'source tuberack ' + str(i+1))
        for i, slot in enumerate(['1', '2', '3', '4'])
    ]
    dest_plate = ctx.load_labware(
        'nest_96_wellplate_2ml_deep', '8', '96-deepwell sample plate')
    resbb = ctx.load_labware(
        'nest_12_reservoir_15ml', '11',
        '12,6 ml reservoir for binding buffer')
    binding_buffer = resbb.wells()[:4]
    # binding_buffer = ctx.load_labware(
    #     'biorad_96_wellplate_200ul_pcr', '11',
    #     '50ml tuberack for lysis buffer + PK (tube A1)').wells()[1]
    tipracks300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot,
                                     '300µl filter tiprack')
                    for slot in ['10', '7']]
    tipracks20 = [ctx.load_labware('opentrons_96_filtertiprack_20ul', '6',
                                   '20µl filter tiprack')]

    # load pipette
    m20 = ctx.load_instrument('p20_multi_gen2', 'left', tip_racks=tipracks20)
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'right', tip_racks=tipracks300)

    # setup samples
    sources = [
        well for rack in source_racks for well in rack.wells()][:NUM_SAMPLES]
    dests_single = dest_plate.wells()[:NUM_SAMPLES]
    num_cols = math.ceil(NUM_SAMPLES/8)
    dests_multi = dest_plate.rows()[0][:num_cols]

    tip_log = {'count': {}}
    folder_path = '/data/A'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips1000' in data:
                    tip_log['count'][m300] = data['tips300']
                else:
                    tip_log['count'][m300] = 0
                if 'tips20' in data:
                    tip_log['count'][m20] = data['tips20']
                else:
                    tip_log['count'][m20] = 0
    else:
        tip_log['count'] = {m300: 0, m20: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tipracks300 for tip in rack.rows()[0]],
        #m20: [tip for rack in tipracks20 for tip in rack.rows()[0]]
        m20: [tip for rack in tipracks20 for tip in rack.rows()[0]]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [m300, m20]
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

#    heights = {binding_buffer: TUBE50_VOlUME * 1}
#   radius = (binding_buffer.diameter)/2
#  min_h = 5

#    def h_track(vol, tube):
#        nonlocal heights
#        dh = vol/(math.pi*(radius**2))
#        if heights[tube] - dh > min_h:
#            heights[tube] = heights[tube] - dh
#        else:
#            heights[tube] = min_h  # stop 5mm short of the bottom
#        return heights[tube]

    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 60
    m300.flow_rate.blow_out = 100


  # transfer internal control + proteinase K
    pick_up(m20)
    for d in dests_multi:
        m20.dispense(10, ic_pk.bottom(2))
        m20.transfer(ICPK_VOlUME, ic_pk.bottom(2), d.bottom(2), air_gap=5,
                     new_tip='never')
        m20.air_gap(5)
    m20.drop_tip()


    # # transfer binding buffer and mix
    # pick_up(m300)
    # for i, (s, d) in enumerate(zip(sources, dests_multi)):
    #
    #     source = binding_buffer[i//96]  # 1 tube of binding buffer can accommodate all samples here
    #     h = h_track(275, source)
    #     # custom mix
    #     m300.flow_rate.aspirate = 100
    #     m300.flow_rate.dispense = 100
    #     m300.dispense(500, source.bottom(h+20))
    #     for _ in range(4):
    #         # m300.air_gap(500)
    #         m300.aspirate(500, source.bottom(h))
    #         m300.dispense(500, source.bottom(h+20))

    pick_up(m300)
    
    for i in range(math.ceil(NUM_SAMPLES/2)):
        bbsrc = binding_buffer[i//(12//len(binding_buffer))]
        if NUM_SAMPLES % 2 != 0 and i == math.ceil(NUM_SAMPLES/2) - 1:
            dest_set = [dest_plate.wells()[NUM_SAMPLES-1]]
        else:
            dest_set = dest_plate.wells()[i*2:i*2+2]
        for i in range(len(dest_set)):
            #h = h_track(BB_VOLUME, binding_buffer)
            if i == 0:
                m300.mix(MIX_REPETITIONS, MIX_VOLUME, bbsrc)
            m300.aspirate(BB_VOLUME/3, bbsrc)
            m300.air_gap(20)
        for s in dest_set:
            m300.dispense(BB_VOLUME/3 + 20, s)
        for i in range(len(dest_set)):
            #h = h_track(BB_VOLUME, binding_buffer)
            if i == 0:
                m300.mix(MIX_REPETITIONS, MIX_VOLUME, bbsrc)
            m300.aspirate(BB_VOLUME/3, bbsrc)
            m300.air_gap(20)
        for s in dest_set:
            m300.dispense(BB_VOLUME/3 + 20, s)
        for i in range(len(dest_set)):
            #h = h_track(BB_VOLUME, binding_buffer)
            if i == 0:
                m300.mix(MIX_REPETITIONS, MIX_VOLUME, bbsrc)
            m300.aspirate(BB_VOLUME/3, bbsrc)
            m300.air_gap(20)
        for s in dest_set:
            m300.dispense(BB_VOLUME/3 + 20, s)

    m300.drop_tip()

    ctx.comment('Move deepwell plate (slot 4) to Station B for RNA \
extraction.')

    # track final used tip
    if not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips1000': tip_log['count'][m300],
            'tips20': tip_log['count'][m20]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
