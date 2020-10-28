from opentrons import protocol_api
import json
import os

# metadata
metadata = {
    'protocolName': 'Version 1 S14 Station C Thermo Taqpath P20 Multi',
    'author': 'Nick <protocols@opentrons.com>',
    'source': 'Custom Protocol Request',
    'apiLevel': '2.3'
}

#pick de amostras das 3 placas das pools para preparar o PCR 2 de confirmação.

plate_1_wells = "A1,B1"
plate_2_wells = "A1,C1"
plate_3_wells = "A2,B2"
SAMPLE_VOL = 10
TIP_TRACK = False


def run(ctx: protocol_api.ProtocolContext):
    global MM_TYPE

    # check source (elution) labware type
    source_plates = [
        ctx.load_labware('opentrons_96_aluminumblock_nest_wellplate_100ul',
                         slot, 'chilled elution plate on block from Station B')
        for slot in ['1', '2', '3']]
    tips20 = [
        ctx.load_labware('opentrons_96_filtertiprack_20ul', slot)
        for slot in ['6', '9', '10', '11']
    ]
    tempdeck = ctx.load_module('Temperature Module Gen2', '4')
    pcr_plate = tempdeck.load_labware(
        'opentrons_96_aluminumblock_nest_wellplate_100ul', 'PCR plate')
    tempdeck.set_temperature(4)

    # pipette
    p20 = ctx.load_instrument('p20_single_gen2', 'right', tip_racks=tips20)

    # setup up sample sources and destinations
    sources = [
        plate.wells_by_name()[name]
        for plate, set in zip(source_plates,
                              [plate_1_wells, plate_2_wells, plate_3_wells])
        for name in set.split(',')]
    sample_dests = pcr_plate.rows()[0][:len(sources)]

    tip_log = {'count': {}}
    folder_path = '/data/C'
    tip_file_path = folder_path + '/tip_log.json'
    if TIP_TRACK and not ctx.is_simulating():
        if os.path.isfile(tip_file_path):
            with open(tip_file_path) as json_file:
                data = json.load(json_file)
                if 'tips20' in data:
                    tip_log['count'][p20] = data['tips20']
                else:
                    tip_log['count'][p20] = 0
        else:
            tip_log['count'] = {p20: 0}
    else:
        tip_log['count'] = {p20: 0}

    tip_log['tips'] = {p20: [tip for rack in tips20 for tip in rack.wells()]}
    tip_log['max'] = {p20: len(tip_log['tips'][p20])}

    def pick_up(pip):
        nonlocal tip_log
        if tip_log['count'][pip] == tip_log['max'][pip]:
            ctx.pause('Replace ' + str(pip.max_volume) + 'µl tipracks before \
resuming.')
            pip.reset_tipracks()
            tip_log['count'][pip] = 0
        pip.pick_up_tip(tip_log['tips'][pip][tip_log['count'][pip]])
        tip_log['count'][pip] += 1

    # transfer samples to corresponding locations
    for s, d in zip(sources, sample_dests):
        pick_up(p20)
        p20.transfer(SAMPLE_VOL, s.bottom(2), d.bottom(2), new_tip='never')
        p20.mix(1, 10, d.bottom(2))
        p20.blow_out(d.top(-2))
        p20.aspirate(5, d.top(2))  # suck in any remaining droplets on way to trash
        p20.drop_tip()

    # track final used tip
    if TIP_TRACK and not ctx.is_simulating():
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        data = {'tips20': tip_log['count'][p20]}
        with open(tip_file_path, 'w') as outfile:
            json.dump(data, outfile)
