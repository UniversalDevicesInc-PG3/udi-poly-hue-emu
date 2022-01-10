#!/usr/bin/env python3
"""
This is a Hue Emulatore NodeServer for Polyglot V3
by JimBoCA jimboca3@gmail.com
"""

from udi_interface import Interface,LOGGER
import sys
import time
from nodes import Controller

if __name__ == "__main__":
    config_dir = "config"
    if not os.path.exists(config_dir):
        try:
            os.mkdir(config_dir)
        except (Exception) as err:
            LOGGER.error("Unable to mkdir {}: {}".format(config_dir,err))
            sys.exit(1)
    if sys.version_info < (3, 6):
        LOGGER.error("ERROR: Python 3.6 or greater is required not {}.{}".format(sys.version_info[0],sys.version_info[1]))
        sys.exit(1)
    try:
        polyglot = Interface([Controller])
        polyglot.start()
        control = Controller(polyglot, 'controller', 'controller', 'Hue Emulator Controller')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        polyglot.stop()
        sys.exit(0)
