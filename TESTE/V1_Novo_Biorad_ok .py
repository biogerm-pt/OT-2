from opentrons.types import Point
import json
import os
import math
import threading
from time import sleep

metadata = {
    'protocolName': 'V1_Novo_BioRad',
    'adapted by': 'Ricardo Magalhães',
    'author': 'Ricardo Magalhães',
    'apiLevel': '2.3'
}

NUM_SAMPLES = 48 # start with 8 samples, slowly increase to 48, then 94 (max is 64)



#NÃO MEXER

TRANSFER_VOL = 5
POOL = False
TIP_TRACK = False
PARK = False
LOCBOTTOM = 7.5
LOCBPCR = 1.5
SIDEBOTTOM = 0
INCUBATION_TIME = 5
MAGHEIGHT = 7.2
#NÃO MEXER


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
    tips300 = [ctx.load_labware('opentrons_96_tiprack_300ul', slot, '200µl filtertiprack')
               for slot in ['5', '6']]
    m300 = ctx.load_instrument(
        'p300_multi_gen2', 'left', tip_racks=tips300)

    magdeck = ctx.load_module('magnetic module gen2', '4')
    magdeck.disengage()
    magheight = MAGHEIGHT
    #magplate
    magplate = magdeck.load_labware('vwr_96_wellplate_2000ul')
    #magplate
    tempdeck = ctx.load_module('Temperature Module Gen2', '1')
    flatplate = tempdeck.load_labware(
                'opentrons_96_aluminumblock_nest_wellplate_100ul',)
    

    if POOL:
        mag_samples_m = magplate.rows()[0][:num_cols] + magplate.rows()[0][8:8+math.ceil(num_cols/2)]
        elution_samples_m = flatplate.rows()[0][:num_cols] + flatplate.rows()[0][8:8+math.ceil(num_cols/2)]
    else:
        mag_samples_m = magplate.rows()[0][:num_cols]
        elution_samples_m = flatplate.rows()[0][:num_cols]

    magdeck.disengage()  # just in case
    #tempdeck.set_temperature(20)

    m300.flow_rate.aspirate = 30
    m300.flow_rate.dispense = 30
    m300.flow_rate.blow_out = 100

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
    drop_threshold = 240  # number of tips trash will accommodate before prompting user to empty

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
            # if not ctx._hw_manager.hardware.is_simulator:
            #     cancellationToken.set_true()
            # thread = create_thread(ctx, cancellationToken)
            m300.home()
            ctx.pause('Please empty tips from waste before resuming.')

            ctx.home()  # home before continuing with protocol
            # cancellationToken.set_false()  # stop light flashing after home
            # thread.join()
            drop_count = 0




    def elute(vol, park=True):
        # transfer samples 
        for m, e in zip(mag_samples_m, elution_samples_m):
            pick_up(m300)
            side_ind = int(m.display_name.split(' ')[0][1:])
            side = 1 if side_ind % 2 == 0 else -1
            loc = m.bottom(LOCBOTTOM).move(Point(x=side*SIDEBOTTOM))  # mudei de LOCBOTTOM  3>2.5
            fin = e.bottom(LOCBOTTOM)
            m300.transfer(vol, loc, fin, air_gap=20, new_tip='never')
            m300.mix(2, vol,fin)
            m300.blow_out(e.top(-2))
            m300.air_gap(20)
            m300.drop_tip()


    magdeck.engage(height=magheight)
    ctx.delay(minutes=INCUBATION_TIME, msg='Incubating on MagDeck for 5 minutes.')

    # transfer

    m300.flow_rate.aspirate = 10
    m300.flow_rate.dispense = 30
    m300.flow_rate.blow_out = 100

    elute(TRANSFER_VOL, park=PARK)
    magdeck.disengage()