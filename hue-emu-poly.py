#!/usr/bin/env python3
"""
This is a NodeServer to Emulate a Hue Hub for Polyglot v2 written in Python3
by JimBo (Jim Searle) jimboca3@gmail.com
"""
import polyinterface
import sys
import time
from ISYHueEmulator import ISYHueEmulator
from traceback import format_exception
from threading import Thread,Event
from hue_emu_funcs import get_network_ip

LOGGER = polyinterface.LOGGER

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Hue Emulator Controller'
        self.isy_hue_emu = False

    def start(self):
        LOGGER.info('Starting HueEmulator Controller')
        self.check_params()
        self.connect()

    def shortPoll(self):
        pass

    def longPoll(self):
        pass

    def query(self):
        pass

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def refresh(self, *args, **kwargs):
        pass

    def connect(self):
        LOGGER.info('Starting thread if ISYHueEmulator')
        self.client_status = "init"
        self.event = Event()
        self.thread = Thread(target=self._connect)
        self.thread.daemon = True
        return self.thread.start()

    def _connect(self):
        # TODO: Can we get the ISY info from Polyglot?  If not, then document these
        self.isy_hue_emu = ISYHueEmulator(
            get_network_ip("8.8.8.8"),
            self.polyConfig['customParams']['port'],
            self.polyConfig['customParams']['isy_host'],
            self.polyConfig['customParams']['isy_port'],
            self.polyConfig['customParams']['isy_user'],
            self.polyConfig['customParams']['isy_password']
            )

    def check_params(self):
        """
        This is an example if using custom Params for user and password and an example with a Dictionary
        """
        default_port = "80"
        if 'port' in self.polyConfig['customParams']:
            self.port = self.polyConfig['customParams']['port']
        else:
            self.port = default_port
            LOGGER.info('check_params: port not defined in customParams, set to default {}'.format(self.port))
            st = False

        # Make sure they are in the params
        self.addCustomParam({'port': self.port})

        # Remove all existing notices
        self.removeNoticesAll()
        # Add a notice if they need to change the user/password from the default.
        #if self.user == default_user or self.password == default_password:
        #    self.addNotice("Please set proper user and password in configuration page, and restart this nodeserver")

    def cmd_update_profile(self,command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    def cmd_refresh(self,command):
        LOGGER.info('refresh:')
        if self.isy_hue_emu is False:
            LOGGER.error('No Hue Emulator?')
            return
        self.isy_hue_emu.refresh()

    id = 'controller'
    commands = {
        'REFRESH': cmd_refresh,
        'UPDATE_PROFILE': cmd_update_profile,
    }
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2}]


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('HueEmulator')
        """
        Instantiates the Interface to Polyglot.
        """
        polyglot.start()
        """
        Starts MQTT and connects to Polyglot.
        """
        control = Controller(polyglot)
        """
        Creates the Controller Node and passes in the Interface
        """
        control.runForever()
        """
        Sits around and does nothing forever, keeping your program running.
        """
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
        """
        Catch SIGTERM or Control-C and exit cleanly.
        """
