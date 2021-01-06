from opentrons import protocol_api 
import json
import os
import math
import threading
from time import sleep

metadata = {'apiLevel': '2.5'}

NUM_SAMPLES = 24
SAMPLE_VOLUME = 475


def run(protocol: protocol_api.ProtocolContext):
    source = protocol.load_labware('starlab_96_wellplate_2000ul', 2)
    dest = protocol.load_labware('starlab_96_wellplate_2000ul', 3)
    tiprack_1 = protocol.load_labware('opentrons_96_filtertiprack_200ul', 6)
    m300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks=[tiprack_1])
    
    

    s = source.wells_by_name()['A1']
    side = 1 
    loc = s.bottom(0.8).move(Point(x=side*2.5)) # mudei de 0.5>0.8  3>2.5

    d = dest.wells_by_name()['A12']

    m300.transfer(SAMPLE_VOLUME, loc, d)
