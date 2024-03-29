from opentrons import protocol_api
import json
import os
import math

# metadata
metadata = {
    'protocolName': 'Version 1 S14 Station C Thermo Taqpath P20 Multi',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 96  # start with 8 samples, slowly increase to 48, then 94 (max is 94)
SAMPLE_VOL = 10
PREPARE_MASTERMIX = False
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):
    global MM_TYPE

    # check source (elution) labware type
    source_plate = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '1',
        'chilled elution plate on block from Station B')
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['2', '3']
    ]
    tips300 = [ctx.load_labware('opentrons_96_filtertiprack_200ul', '9')]
    tempdeck = ctx.load_module('Temperature Module Gen2', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', 'PCR plate')
    mm_strips = ctx.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', '5',
        'mastermix strips')
    
    #TEMPERATURE
    tempdeck.set_temperature(8)


    tube_block = ctx.load_labware(
        'opentrons_24_aluminumblock_nest_2ml_snapcap', '8',
        '2ml screw tube aluminum block for mastermix + controls')

    # pipette
    m20 = ctx.load_instrument('p20_multi_gen2', 'right', tip_racks=tips20)
    p300 = ctx.load_instrument('p300_single_gen2', 'left', tip_racks=tips300)

    # setup up sample sources and destinations
    num_cols = math.ceil(NUM_SAMPLES/8)
    sources = source_plate.rows()[0][:num_cols]
    sample_dests = pcr_plate.rows()[0][:num_cols]

    tip_log = {'count': {}}
    folder_path = '/data/C'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips20' in data:
                    tip_log['count'][m20] = data['tips20']
                else:
                    tip_log['count'][m20] = 0
                if 'tips300' in data:
                    tip_log['count'][p300] = data['tips300']
                else:
                    tip_log['count'][p300] = 0
        else:
            tip_log['count'] = {m20: 0, p300: 0}
    else:
        tip_log['count'] = {m20: 0, p300: 0}

    tip_log['tips'] = {
        m20: [tip for rack in tips20 for tip in rack.rows()[0]],
        p300: [tip for rack in tips300 for tip in rack.wells()]
    }
    tip_log['max'] = {
        pip: len(tip_log['tips'][pip])
        for pip in [m20, p300]
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

    """ mastermix component maps """
    mm_tube = tube_block.wells()[0]
    mm_dict = {
        'volume': 15,
        'components': {
            tube: vol for tube, vol in zip(tube_block.columns()[1][:3],
                                           [6.25, 1.25, 7.5])
        }
    }

    vol_overage = 1.01 if NUM_SAMPLES > 48 else 1.02  # decrease overage for small sample number
    total_mm_vol = mm_dict['volume']*(NUM_SAMPLES+2)*vol_overage
    # translate total mastermix volume to starting height
    r = mm_tube.diameter/2
    mm_height = total_mm_vol/(math.pi*(r**2)) - 5

    def h_track(vol):
        nonlocal mm_height
        dh = 1.1*vol/(math.pi*(r**2))  # compensate for 10% theoretical volume loss
        mm_height = mm_height - dh if mm_height - dh > 2 else 2  # stop at 2mm above mm tube bottom
        return mm_tube.bottom(mm_height)

    def mix_up_down(reps, vol, loc, pip):
        for _ in range(reps):
            pip.aspirate(vol, loc.bottom(5))
            pip.dispense(vol, loc.bottom(loc._depth/2), 3)
            #pip.dispense(vol, loc.top(), 3)
            pip.aspirate(vol, loc.bottom(5))
            pip.dispense(vol, loc.top())

    if PREPARE_MASTERMIX:
        vol_overage = 1.1 if NUM_SAMPLES > 48 else 1.04

        for i, (tube, vol) in enumerate(mm_dict['components'].items()):
            comp_vol = vol*(NUM_SAMPLES)*vol_overage
            pick_up(p300)
            num_trans = math.ceil(comp_vol/160)
            vol_per_trans = comp_vol/num_trans
            for _ in range(num_trans):
                p300.air_gap(20)
                p300.aspirate(vol_per_trans, tube.bottom(1.5), 0.4)
                ctx.delay(seconds=3)
                p300.touch_tip(tube)
                p300.air_gap(20)
                p300.dispense(20, mm_tube.top())  # void air gap
                p300.dispense(vol_per_trans, mm_tube.bottom(2))
                p300.dispense(20, mm_tube.top())  # void pre-loaded air gap
                p300.blow_out(mm_tube.top())
                p300.touch_tip(mm_tube)
            if i < len(mm_dict['components'].items()) - 1:  # only keep tip if last component and p300 in use
                p300.drop_tip()
        mm_total_vol = mm_dict['volume']*(NUM_SAMPLES)*vol_overage
        if not p300.hw_pipette['has_tip']:  # pickup tip with P300 if necessary for mixing
            pick_up(p300)
        mix_vol = mm_total_vol / 2 if mm_total_vol / 2 <= 200 else 200  # mix volume is 1/2 MM total, maxing at 200µl
        # mix_loc = mm_tube.bottom(10) if NUM_SAMPLES > 48 else mm_tube.bottom(5)
        # mix_loc2 = mm_tube.bottom(20) if NUM_SAMPLES > 48 else mm_tube.bottom(10)
        #p300.flow_rate.aspirate = 15
        mix_up_down(10, mix_vol, mm_tube, p300)
        # p300.mix(15, mix_vol, mix_loc, 3)
        # p300.mix(15, mix_vol, mix_loc2, 4)
        #p300.flow_rate.aspirate = 150
        p300.blow_out(mm_tube.top())
        p300.touch_tip()

    # transfer mastermix to strips
    mm_strip = mm_strips.columns()[0]
    if not p300.hw_pipette['has_tip']:
        pick_up(p300)
    for i, well in enumerate(mm_strip):
        if NUM_SAMPLES % 8 == 0 or i < NUM_SAMPLES % 8:
            vol = num_cols*mm_dict['volume']*((vol_overage-1)/2+1)
        else:
            vol = (num_cols-1)*mm_dict['volume']*((vol_overage-1)/2+1)
        p300.flow_rate.aspirate = 15
        p300.transfer(vol, mm_tube.bottom(1), well, new_tip='never')
    p300.drop_tip()

    # transfer mastermix to plate
    mm_vol = mm_dict['volume']
    pick_up(m20)
    m20.mix(5, mm_vol, mm_strip[0], 3)
    m20.transfer(mm_vol, mm_strip[0].bottom(0.5), sample_dests,
                 new_tip='never')
    m20.drop_tip()

    # transfer samples to corresponding locations
    for s, d in zip(sources, sample_dests):
        pick_up(m20)
        m20.transfer(SAMPLE_VOL, s.bottom(1), d.bottom(1), new_tip='never')
        m20.mix(1, 10, d.bottom(1))
        m20.blow_out(d.top(-2))
        m20.aspirate(5, d.top(2))  # suck in any remaining droplets on way to trash
        m20.drop_tip()

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {
            'tips20': tip_log['count'][m20],
            'tips300': tip_log['count'][p300]
        }
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
