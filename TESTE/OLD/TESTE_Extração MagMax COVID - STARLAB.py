from opentrons.types import Point
import json
import os
import math
import threading
from time import sleep

metadata = {
    'protocolName': 'USO_v6_station_b_M300_Pool_magmax',
    'author': 'Nick <ndiehl@opentrons.com',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 8 # start with 8 samples, slowly increase to 48, then 94 (max is 64)
ELUTION_VOL = 50
STARTING_VOL = 540
WASH_VOL = 500
POOL = False
TIP_TRACK = False
PARK = True

# Definitions for deck light flashing
class CancellationToken:
    def __init__(self):
       self.is_continued = False

    def set_true(self):
       self.is_continued = True

    def set_false(self):
       self.is_continued = False


def turn_on_blinking_notification(hardware, pause):
    while pause.is_continued:
        hardware.set_lights(rails=True)
        sleep(1)
        hardware.set_lights(rails=False)
        sleep(1)

def create_thread(ctx, cancel_token):
    t1 = threading.Thread(target=turn_on_blinking_notification, args=(ctx._hw_manager.hardware, cancel_token))
    t1.start()
    return t1

# Start protocol
def run(ctx):
    # Setup for flashing lights notification to empty trash
    # cancellationToken = CancellationToken()

    # load labware and pipettes
    num_cols = math.ceil(NUM_SAMPLES/8)
    tips300 = [ctx.load_labware('starlab_96_tiprack_300ul', slot, '200µl filtertiprack')
               for slot in ['3', '6', '8', '9', '7']]
    if PARK:
        parkingrack = ctx.load_labware(
            'starlab_96_tiprack_300ul', '10', 'empty tiprack for parking')
        if POOL:
            parking_spots = parkingrack.rows()[0]
        else:
            parking_spots = parkingrack.rows()[0][:num_cols]
    else:
        tips300.insert(0, ctx.load_labware('starlab_96_tiprack_300ul', '10',
                                           '200µl filtertiprack'))
        parking_spots = [None for none in range(12)]

    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'left', tip_racks=tips300)

    magdeck = ctx.load_module('magnetic module gen2', '4')
    magdeck.disengage()
    magheight = 6.5
    magplate = magdeck.load_labware('nest_96_wellplate_2ml_deep')
    # magplate = magdeck.load_labware('biorad_96_wellplate_200ul_pcr')
    tempdeck = ctx.load_module('Temperature Module Gen2', '1')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    waste = ctx.load_labware('nest_1_reservoir_195ml', '11',
                             'Liquid Waste').wells()[0].top()
    etoh = ctx.load_labware(
        'nest_1_reservoir_195ml', '2', 'EtOH reservoir').wells()[0:]
    res1 = ctx.load_labware(
        'nest_12_reservoir_15ml', '5', 'reagent reservoir 1')
    wash1 = res1.wells()[:4]
    elution_solution = res1.wells()[-1]

    if POOL:
        mag_samples_m = magplate.rows()[0][:num_cols] + magplate.rows()[0][8:8+math.ceil(num_cols/2)]
        elution_samples_m = flatplate.rows()[0][:num_cols] + flatplate.rows()[0][8:8+math.ceil(num_cols/2)]
    else:
        mag_samples_m = magplate.rows()[0][:num_cols]
        elution_samples_m = flatplate.rows()[0][:num_cols]

    magdeck.disengage()  # just in case
    #tempdeck.set_temperature(20)

    m300.flow_rate.aspirate = 50
    m300.flow_rate.dispense = 150
    m300.flow_rate.blow_out = 300

    folder_path = '/data/B'
    tip_file_path = folder_path + '/tip_log.json'
    tip_log = {'count': {}}
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips300' in data:
                    tip_log['count'][m300] = data['tips300']
                else:
                    tip_log['count'][m300] = 0
        else:
            tip_log['count'][m300] = 0
    else:
        tip_log['count'] = {m300: 0}

    tip_log['tips'] = {
        m300: [tip for rack in tips300 for tip in rack.rows()[0]]}
    tip_log['max'] = {m300: len(tip_log['tips'][m300])}

    def pick_up(pip, loc=None):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip] and not loc:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        if loc:
            pip.pick_up_tip(loc)
        else:
            pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
            tip_log['count'][pip] += 1

    switch = True
    drop_count = 0
    drop_threshold = 10  # number of tips trash will accommodate before prompting user to empty

    def drop(pip):
        nonlocal switch
        nonlocal drop_count
        side = 30 if switch else -18
        drop_loc = ctx.loaded_labwares[12].wells()[0].top().move(
            Point(x=side))
        pip.drop_tip(drop_loc)
        switch = not switch
        drop_count += 8
        if drop_count == drop_threshold:
            # Setup for flashing lights notification to empty trash
            if not ctx._hw_manager.hardware.is_simulator:
                cancellationToken.set_true()
            thread = create_thread(ctx, cancellationToken)
            m300.home()
            ctx.pause('Please empty tips from waste before resuming.')

            ctx.home()  # home before continuing with protocol
            cancellationToken.set_false()  # stop light flashing after home
            thread.join()
            drop_count = 0

    waste_vol = 0
    waste_threshold = 185000

    def remove_supernatant(vol, park=False):

        def waste_track(vol):
            nonlocal waste_vol
            if waste_vol + vol >= waste_threshold:
                # Setup for flashing lights notification to empty liquid waste
                if not ctx._hw_manager.hardware.is_simulator:
                     cancellationToken.set_true()
                thread = create_thread(ctx, cancellationToken)
                m300.home()
                ctx.pause('Please empty liquid waste (slot 11) before resuming.')

                ctx.home()  # home before continuing with protocol
                cancellationToken.set_false() # stop light flashing after home
                thread.join()
                waste_vol = 0
            waste_vol += vol

        m300.flow_rate.aspirate = 30
        num_trans = math.ceil(vol/200)
        vol_per_trans = vol/num_trans
        for m, spot in zip(mag_samples_m, parking_spots):
            if park:
                pick_up(m300, spot)
            else:
                pick_up(m300)
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = 1 if side_ind % 2 == 0 else -1
            loc = m.bottom(0.8).move(Point(x=side*2.5)) # mudei de 0.5>0.8  3>2.5
            for _ in range(num_trans):
                waste_track(vol_per_trans)
                if m300.current_volume > 0:
                    m300.dispense(m300.current_volume, m.top())  # void air gap if necessary
                m300.move_to(m.center())
                m300.transfer(vol_per_trans, loc, waste, new_tip='never',
                              air_gap=10)
                #m300.blow_out(waste)
                m300.air_gap(10)
            drop(m300)
        m300.flow_rate.aspirate = 50  # mudei de 150


    def wash(wash_vol, source, mix_reps, park=True):
        magdeck.disengage()

        num_trans = math.ceil(wash_vol/200)
        vol_per_trans = wash_vol/num_trans
        wash_vol_rem = wash_vol
        for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = -1 if side_ind % 2 == 0 else 1
            pick_up(m300)
            loc = m.bottom(0.8).move(Point(x=side*2.5)) # mudei de 0.5>0.8  3>2.5
            src = source[i//(12//len(source))]
            for n in range(num_trans):
                if m300.current_volume > 0:
                    m300.dispense(m300.current_volume, src.top())
                m300.transfer(vol_per_trans, src.bottom(0.8), m.top(), air_gap=20,
                              new_tip='never')
                if n < num_trans - 1:  # only air_gap if going back to source
                    m300.air_gap(20)
            m300.mix(mix_reps, 150, loc)
            m300.blow_out(m.top())
            m300.air_gap(20)
            if park:
                m300.drop_tip(spot)
            else:
                drop(m300)

        magdeck.engage(height=magheight)
        ctx.delay(minutes=5, msg='Incubating on MagDeck for 5 minutes.')

        remove_supernatant(wash_vol_rem+40, park=park) #+40

    def wash_etoh(wash_etoh_vol, source_etoh, mix_reps_etoh, park=True):
        magdeck.disengage()

        num_trans = math.ceil(wash_etoh_vol/200)
        vol_per_trans = wash_etoh_vol/num_trans
        for i, (m, spot) in enumerate(zip(mag_samples_m, parking_spots)):
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = -1 if side_ind % 2 == 0 else 1
            pick_up(m300)
            loc = m.bottom(0.5).move(Point(x=side*2.5)) # mudei de 0.5  3>2.5
            src = source_etoh[i//(12//len(source_etoh))]
            for n in range(num_trans):
                if m300.current_volume > 0:
                    m300.dispense(m300.current_volume, src.top())
                m300.transfer(vol_per_trans, src.bottom(0.8), m.top(), air_gap=20,
                              new_tip='never')
                if n < num_trans - 1:  # only air_gap if going back to source_etoh
                    m300.air_gap(20)
            m300.mix(mix_reps_etoh, 150, loc)
            m300.blow_out(m.top())
            m300.air_gap(20)
            if park:
                m300.drop_tip(spot)
            else:
                drop(m300)

        magdeck.engage(height=magheight)
        ctx.delay(minutes=5, msg='Incubating on MagDeck for 5 minutes.')

        remove_supernatant(wash_etoh_vol+40, park=park) #+40



    def elute(vol, park=True):
        # resuspend beads in elution
        for m, spot in zip(mag_samples_m, parking_spots):
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = -1 if side_ind % 2 == 0 else 1
            pick_up(m300)
            loc = m.bottom(0.8).move(Point(x=side*2.5)) # mudei de 0.5>0.8  3>2.5
            m300.aspirate(vol, elution_solution)
            m300.move_to(m.center())
            m300.dispense(vol, loc)
            m300.mix(10, 0.8*vol, loc)
            m300.blow_out(m.bottom(5))
            m300.air_gap(20)
            if park:
                m300.drop_tip(spot)
            else:
                drop(m300)

        ctx.delay(minutes=5, msg='Incubating off magnet at room temperature \
for 5 minutes')  
        magdeck.engage(height=magheight)
        ctx.delay(minutes=5, msg='Incubating on magnet at room temperature \
for 5 minutes')  

        for m, e, spot in zip(mag_samples_m, elution_samples_m, parking_spots):
            if park:
                pick_up(m300, spot)
            else:
                pick_up(m300)
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = 1 if side_ind % 2 == 0 else -1
            loc = m.bottom(0.8).move(Point(x=side*2.5))  # mudei de 0.5>0.8  3>2.5
            m300.transfer(40, loc, e.bottom(5), air_gap=20, new_tip='never')
            m300.blow_out(e.top(-2))
            m300.air_gap(20)
            m300.drop_tip()

    magdeck.engage(height=magheight)
    ctx.delay(minutes=0.5, msg='Incubating on MagDeck for 5 minutes.')

    # remove initial supernatant

    m300.flow_rate.aspirate = 50
    remove_supernatant(STARTING_VOL, park=PARK)
    wash(WASH_VOL, wash1, 15, park=PARK)
    #m300.flow_rate.aspirate = 94
    wash_etoh(WASH_VOL, etoh, 15, park=PARK)
    wash_etoh(WASH_VOL, etoh, 15, park=PARK)

    magdeck.disengage()
    ctx.delay(minutes=5, msg='Airdrying beads at room temperature for 5 \
minutes.')
    m300.flow_rate.aspirate = 50
    elute(ELUTION_VOL, park=PARK)
