#!/usr/bin/env python3
"""
This is a NodeServer to Emulate a Hue Hub for Polyglot v2 written in Python3
by JimBo (Jim Searle) jimboca3@gmail.com
"""
import polyinterface
import sys
import time
import logging
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
        self.l_info('start','Starting HueEmulator Controller')
        # New vesions need to force an update
        self.check_version()
        self.check_params()
        self.set_listen(self.get_listen())
        self.set_debug_level(self.getDriver('GV1'))
        self.connect()
        self.l_info('start','done')

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
        self.l_info('connect','Starting thread for ISYHueEmulator')
        # TODO: Can we get the ISY info from Polyglot?  If not, then document these
        self.isy_hue_emu = ISYHueEmulator(
            get_network_ip("8.8.8.8"),
            self.hue_port,
            self.isy_host,
            self.isy_port,
            self.isy_user,
            self.isy_password,
            )
        self.client_status = "init"
        self.event = Event()
        self.thread = Thread(target=self._connect)
        self.thread.daemon = True
        return self.thread.start()

    def _connect(self):
        listen = True
        if self.get_listen() == 0:
            listen = False
        self.l_info("_connect","listen={}".format(listen))
        self.thread = Thread(target=self.isy_hue_emu.connect(listen))

    def check_version(self):
        current_version = 4
        if 'cver' in self.polyConfig['customData']:
            cver = self.polyConfig['customData']['cver']
        else:
            cver = 0
        self.l_debug("start","cver={} current_version={}".format(cver,current_version))
        if cver < current_version:
            self.l_debug("start","updating myself since cver {} < {}".format(cver,current_version))
            st = self.poly.installprofile()
            # Force an update.
            self.addNode(self,update=True)
            self.polyConfig['customData']['cver'] = current_version
            self.saveCustomData(self.polyConfig['customData'])

    def check_params(self):
        """
        This is an example if using custom Params for user and password and an example with a Dictionary
        """
        st = True
        default_port = "8080"
        if 'hue_port' in self.polyConfig['customParams']:
            self.hue_port = self.polyConfig['customParams']['hue_port']
        else:
            self.hue_port = default_port
            self.l_info('check_params','hue_port not defined in customParams, set to default {}'.format(self.hue_port))
            st = False

        default = "192.168.1.xx"
        if 'isy_host' in self.polyConfig['customParams']:
            self.isy_host = self.polyConfig['customParams']['isy_host']
        else:
            self.isy_host = default
        # This can never be the default
        if self.isy_host == default:
            self.l_info('check_params','isy_host not defined in customParams, set to default {}'.format(default))
            st = False

        default = "80"
        if 'isy_port' in self.polyConfig['customParams']:
            self.isy_port = self.polyConfig['customParams']['isy_port']
        else:
            self.isy_port = default
            self.l_info('check_params','isy_port not defined in customParams, set to default {}'.format(default))
            st = False

        default = "admin"
        if 'isy_user' in self.polyConfig['customParams']:
            self.isy_user = self.polyConfig['customParams']['isy_user']
        else:
            self.isy_user = default
            self.l_info('check_params','isy_user not defined in customParams, set to default {}'.format(default))
            st = False

        default = "your_isy_password"
        if 'isy_password' in self.polyConfig['customParams']:
            self.isy_password = self.polyConfig['customParams']['isy_password']
        else:
            self.isy_password = default
        # This can never be the default
        if self.isy_password == default:
            self.l_info('check_params','isy_password not defined in customParams, set to default {}'.format(default))
            st = False

        # Make sure they are in the params
        self.addCustomParam({'hue_port': self.hue_port, 'isy_host': self.isy_host, 'isy_port': self.isy_port, 'isy_user': self.isy_user, 'isy_password': self.isy_password})

        # Remove all existing notices
        self.removeNoticesAll()
        # Add a notice if some params don't look correct.
        if not st:
            self.addNotice("Please set parameters in configuration page and restart this nodeserver")

    def l_info(self, name, string):
        LOGGER.info("Controller:%s: %s" %  (name,string))

    def l_error(self, name, string, exc_info=False):
        LOGGER.error("Controller:%s: %s" % (name,string), exc_info=exc_info)

    def l_warning(self, name, string):
        LOGGER.warning("Controller:%s: %s" % (name,string))

    def l_debug(self, name, string):
        LOGGER.debug("Controller:%s: %s" % (name,string))

    def set_all_logs(self,level):
        LOGGER.setLevel(level)
        #logging.getLogger('requests').setLevel(level)

    def set_debug_level(self,level):
        self.l_info('set_debug_level',level)
        if level is None:
            level = 20
        level = int(level)
        if level == 0:
            level = 20
        self.l_info('set_debug_level','Set GV1 to {}'.format(level))
        self.setDriver('GV1', level)
        # 0=All 10=Debug are the same because 0 (NOTSET) doesn't show everything.
        if level == 10:
            self.set_all_logs(logging.DEBUG)
        elif level == 20:
            self.set_all_logs(logging.INFO)
        elif level == 30:
            self.set_all_logs(logging.WARNING)
        elif level == 40:
            self.set_all_logs(logging.ERROR)
        elif level == 50:
            self.set_all_logs(logging.CRITICAL)
        else:
            self.l_error("set_debug_level","Unknown level {}".format(level))

    def get_listen(self):
        self.l_info('get_listen','')
        val = self.getDriver('GV2')
        if val is None:
            val = 1
        self.l_info('get_listen',val)
        return int(val)

    def set_listen(self,val):
        self.l_info('set_listen','Set to {}'.format(val))
        if self.isy_hue_emu is not False:
            if val == 0:
                self.isy_hue_emu.stop_listener()
            else:
                self.isy_hue_emu.start_listener()
        self.setDriver('GV2', val)

    def cmd_update_profile(self,command):
        self.l_info('update_profile','')
        st = self.poly.installprofile()
        return st

    def cmd_refresh(self,command):
        self.l_info('refresh:')
        if self.isy_hue_emu is False:
            LOGGER.error('No Hue Emulator?')
            return
        self.isy_hue_emu.refresh()

    def cmd_set_debug_mode(self,command):
        val = int(command.get('value'))
        self.l_info("cmd_set_debug_mode",val)
        self.set_debug_level(val)

    def cmd_set_listen(self,command):
        val = int(command.get('value'))
        self.l_info("cmd_set_listen",val)
        self.set_listen(val)

    id = 'controller'
    commands = {
        'REFRESH': cmd_refresh,
        'UPDATE_PROFILE': cmd_update_profile,
        'SET_DEBUGMODE': cmd_set_debug_mode,
        'SET_LISTEN': cmd_set_listen,
    }
    drivers = [
        {'driver': 'ST', 'value': 1, 'uom': 2},
        {'driver': 'GV1', 'value': 20,  'uom': 25}, # integer: Log/Debug Mode
        {'driver': 'GV2', 'value': 0, 'uom': 2} # Listen
    ]

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
                                                                                                                                                                                                                                                                                                                                                                                                                                              
