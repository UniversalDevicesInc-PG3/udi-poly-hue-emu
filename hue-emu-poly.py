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
        # TODO: Can we get the ISY info from Polyglot?  If not, then document these
        self.isy_hue_emu = ISYHueEmulator(
            get_network_ip("8.8.8.8"),
            self.hue_port,
            self.isy_host,
            self.isy_port,
            self.isy_user,
            self.isy_password
            )
        self.client_status = "init"
        self.event = Event()
        self.thread = Thread(target=self.isy_hue_emu.connect)
        self.thread.daemon = True
        return self.thread.start()

    def check_params(self):
        """
        This is an example if using custom Params for user and password and an example with a Dictionary
        """
        default_port = "8080"
        if 'hue_port' in self.polyConfig['customParams']:
            self.hue_port = self.polyConfig['customParams']['hue_port']
        else:
            self.hue_port = default_port
            LOGGER.info('check_params: hue_port not defined in customParams, set to default {}'.format(self.hue_port))
            st = False

        default = "192.168.1.xx"
        if 'isy_host' in self.polyConfig['customParams']:
            self.isy_host = self.polyConfig['customParams']['isy_host']
        else:
            self.isy_host = default
            LOGGER.info('check_params: isy_host not defined in customParams, set to default {}'.format(default))
            st = False

        default = "80"
        if 'isy_port' in self.polyConfig['customParams']:
            self.isy_port = self.polyConfig['customParams']['isy_port']
        else:
            self.isy_port = default
            LOGGER.info('check_params: isy_port not defined in customParams, set to default {}'.format(default))
            st = False

        default = "admin"
        if 'isy_user' in self.polyConfig['customParams']:
            self.isy_user = self.polyConfig['customParams']['isy_user']
        else:
            self.isy_user = default
            LOGGER.info('check_params: isy_user not defined in customParams, set to default {}'.format(default))
            st = False

        if 'isy_password' in self.polyConfig['customParams']:
            self.isy_password = self.polyConfig['customParams']['isy_password']
        else:
            self.isy_password = default
            LOGGER.info('check_params: isy_password not defined in customParams, set to default {}'.format(default))
            st = False

        # Make sure they are in the params
        self.addCustomParam({'hue_port': self.hue_port, 'isy_host': self.isy_host, 'isy_port': self.isy_port, 'isy_user': self.isy_user, 'isy_password': self.isy_password})

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
