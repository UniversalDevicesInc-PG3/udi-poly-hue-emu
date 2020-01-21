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
from threading import Thread
from hue_emu_funcs import get_network_ip,get_server_data

LOGGER = polyinterface.LOGGER

class Controller(polyinterface.Controller):

    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = 'Hue Emulator Controller'
        ifc = self.poly.get_network_interface()
        self.l_info('init','Initializing HueEmulator Controller')
        self.isy_hue_emu = False
        self.sent_cstr = ""
        self.thread = None

    def start(self):
        self.l_info('start','Starting HueEmulator Controller')
        self.serverdata = self.poly.get_server_data(check_profile=True)
        self.l_info('start','Starting HueEmulator Controller {}'.format(self.serverdata['version']))
        # New vesions need to force an update
        self.check_params()
        self.set_listen(self.get_listen())
        self.set_debug_level(self.getDriver('GV1'))
        self.set_isy_connected(False)
        self.connect()
        self.l_info('start','done')

    def shortPoll(self):
        self.l_debug('shortPoll','')
        self.set_isy_connected()
        self.update_config_docs()
        if self.thread is not None:
            if not self.thread.isAlive():
                self.l_error('shortPoll',"Thread is dead, restarting.")

    def longPoll(self):
        pass

    def query(self):
        pass

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def refresh(self, *args, **kwargs):
        self.l_info('refresh','')
        if self.isy_hue_emu is False:
            self.l_error('refresh','No Hue Emulator?')
            return
        self.isy_hue_emu.refresh()
        self.update_config_docs()

    def update_config_docs(self):
        # '<style> table { cellpadding: 10px } </style>'
        self.config_info = [
        '<h1>Spoken Device Table</h1>',
        'This table is refreshed during short poll, so it may be out of date for a few seconds<br>',
        '<table border=1>',
        '<tr><th rowspan=2><center>HueId<th rowspan=2><center>NSId<th colspan=2><center>Property Node/Scene<th colspan=2><center>Scene<th rowspan=2><center>Spoken<th rowspan=2><center>On<th rowspan=2><center>Bri</tr>',
        '<tr><th><center>Id<th><center>Name<th><center>Scene<th><center>Name<th></tr>']
        for i, device in enumerate(self.isy_hue_emu.pdevices):
            # Only used for debug
            if device is False:
                self.config_info.append('<tr><td>{}<td colspan=8>empty</tr>'.format(i))
            elif device.scene is False:
                self.config_info.append('<tr><td>{}<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td colspan=2>&nbsp;None&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;</tr>'.
                format(i,device.id,device.node,device.node.name,device.name,device.on,device.bri))
            else:
                self.config_info.append('<tr><td>{}<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;</tr>'.
                format(i,device.id,device.node,device.node.name,device.scene,device.scene.name,device.name,device.on,device.bri))
        self.config_info.append('</table>')
        s = "\n"
        cstr = s.join(self.config_info)
        if self.sent_cstr != cstr:
            self.poly.add_custom_config_docs(cstr,True)
            self.sent_cstr = cstr

    def connect(self):
        self.l_info('connect','Starting thread for ISYHueEmulator')
        # TODO: Can we get the ISY info from Polyglot?  If not, then document these
        self.isy_hue_emu = ISYHueEmulator(
            ifc['addr'],
            self.hue_port,
            self.isy_host,
            self.isy_port,
            self.isy_user,
            self.isy_password,
            )
        self.client_status = "init"
        self.thread = Thread(target=self._connect)
        self.thread.daemon = True
        return self.thread.start()

    def _connect(self):
        listen = True
        if self.get_listen() == 0:
            listen = False
        self.l_info("_connect","listen={}".format(listen))
        try:
            self.isy_hue_emu.connect(listen)
        except Exception as ex:
            self.l_error("PyISY Connection crashed with {}, will restart on next shortPoll".format(ex), exc_info=True)
        # Thread is dead?
        self.set_isy_connected(False)

    def check_params(self):
        """
        This is an example if using custom Params for user and password and an example with a Dictionary
        """
        # Remove all existing notices
        self.removeNoticesAll()

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

    def set_isy_connected(self,val=None):
        if val is None:
            if self.thread is None:
                val = False
            elif self.isy_hue_emu is False:
                val = False
            elif self.isy_hue_emu.isy_connected():
                val = True
            else:
                val = False
        self.setDriver('GV0', 1 if val else 0)

    def cmd_update_profile(self,command):
        self.l_info('update_profile','')
        st = self.poly.installprofile()
        return st

    def cmd_refresh(self,command):
        self.refresh()

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
        {'driver': 'ST',  'value': 1,  'uom': 2},   # Node Status
        {'driver': 'GV0', 'value': 0,  'uom': 2},   # ISY Connected
        {'driver': 'GV1', 'value': 20, 'uom': 25},  # integer: Log/Debug Mode
        {'driver': 'GV2', 'value': 0,  'uom': 2}    # Listen
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
