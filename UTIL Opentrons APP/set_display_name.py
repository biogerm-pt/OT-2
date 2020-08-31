# This script sets the name that shows up for this robot in the Opentrons App.
# 
# It doesn't change the OT-2's serial number.  If you need to change an OT-2's
# serial number in addition to its display name--like if you've just installed a
# fresh SD card--then there's a different script you should use instead.

# Change this to what you want your OT-2's new display name to be.
# For example: NEW_DISPLAY_NAME = ""
NEW_DISPLAY_NAME = "The Cure"

from opentrons import robot
import os

robot.comment(f"Setting display name to {NEW_DISPLAY_NAME}.")

if not robot.is_simulating():
    with open("/etc/machine-info", "w") as serial_number_file:
        serial_number_file.write(f"DEPLOYMENT=production\nPRETTY_HOSTNAME={NEW_DISPLAY_NAME}\n")
    
    os.sync()
    
    robot.comment("Done.")
