#!/usr/bin/env python3
"""
This is a NodeServer to Emulate a Hue Hub for Polyglot v2 written in Python3
by JimBo (Jim Searle) jimboca3@gmail.com
"""
from polyinterface import Controller,LOGGER,LOG_HANDLER
import sys
import time
import logging
from ISYHueEmu import ISYHueEmu
from traceback import format_exception
from threading import Thread

class HueEmuController(Controller):

    # Number of longPoll calls to timeout listen
    LISTEN_TIMEOUT = 5

    def __init__(self, polyglot):
        super(HueEmuController, self).__init__(polyglot)
        self.name = 'Hue Emulator Controller'
        LOGGER.info('Initializing')
        self.isy_hue_emu = False
        self.ucd_check = False
        self.sent_cstr = ""
        self.thread = None
        self.hb = 0

    def start(self):
        LOGGER.info('Starting')
        self.initializing = True
        self.serverdata = self.poly.get_server_data(check_profile=True)
        LOGGER.info('Version {}'.format(self.serverdata['version']))
        self.net_ifc = self.poly.get_network_interface()
        # New vesions need to force an update
        self.check_params()
        self.check_version()
        # We listen for new connections on restart...
        self.set_listen(1)
        self.set_debug_level(self.getDriver('GV1'))
        self.set_debug_level_hueupnp(self.getDriver('GV3'))
        self.set_isy_connected(False)
        self.heartbeat()
        self.connect()
        LOGGER.info('done')

    def shortPoll(self):
        self.set_isy_connected()
        self.update_config_docs()
        if self.thread is not None:
            if not self.thread.is_alive():
                self.thread = None
                LOGGER.error("Thread is dead, restarting.")
                self.check_params() # Reload in case they changed.
                self.connect()

    def longPoll(self):
        self.heartbeat()
        if self.initializing:
            return
        if self.get_listen() == 1:
            LOGGER.warning('Listen Count = {}'.format(self.listen_cnt))
            if self.listen_cnt > 0:
                self.listen_cnt -= 1
            else:
                self.set_listen(0)

    def heartbeat(self):
        LOGGER.debug('hb={}'.format(self.hb))
        if self.hb == 0:
            self.reportCmd("DON",2)
            self.hb = 1
        else:
            self.reportCmd("DOF",2)
            self.hb = 0


    def query(self):
        self.reportDrivers();

    def delete(self):
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def stop(self):
        LOGGER.debug('NodeServer stopped.')

    def refresh(self, *args, **kwargs):
        LOGGER.info('')
        if self.isy_hue_emu is False:
            LOGGER.error('No Hue Emulator?')
            return
        self.isy_hue_emu.refresh()
        self.update_config_docs()

    def update_config_docs(self):
        # '<style> table { cellpadding: 10px } </style>'
        if self.ucd_check is False:
            try:
                if self.poly.supports_feature('customParamsDoc'):
                    self.ucd = True
                else:
                    LOGGER.error('polyinterface customParamsDoc feature not supported')
                    self.ucd = False
            except AttributeError:
                LOGGER.error('polyinterface supports feature failed?',True)
                self.ucd = False
            self.ucd_check = True
        if self.ucd is False:
            return
        self.config_info = [
        '<h1>Spoken Device Table</h1>',
        'This table is refreshed during short poll, so it may be out of date for a few seconds<br>',
        '<table border=1>',
        '<tr><th rowspan=2><center>HueId<th rowspan=2><center>NSId<th colspan=2><center>Property Node/Scene<th colspan=2><center>Scene<th rowspan=2><center>Spoken<th rowspan=2><center>On<th rowspan=2><center>Bri</tr>',
        '<tr><th><center>Id<th><center>Name<th><center>Scene<th><center>Name<th></tr>']
        if self.isy_hue_emu is not False:
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

    def check_version(self):
        current_version = self.serverdata['version']
        if 'last_version' in self.polyConfig['customData']:
            last_version = self.polyConfig['customData']['last_version']
        else:
            last_version = '0'
        LOGGER.info("last_version={} current_version={}".format(last_version,current_version))
        if last_version != current_version:
            if current_version == '2.2.1':
                LOGGER.info("updating myself since last_version {} < {}".format(last_version,current_version))
                # Force an update.
                self.addNode(self,update=True)
                self.polyConfig['customData']['last_version'] = current_version
                self.saveCustomData(self.polyConfig['customData'])

    def connect(self):
        LOGGER.info('Starting thread for ISYHueEmu')
        # TODO: Can we get the ISY info from Polyglot?  If not, then document these
        self.isy_hue_emu = ISYHueEmu(
            self.net_ifc['addr'],
            self.hue_port,
            self.isy_host,
            self.isy_port,
            self.isy_user,
            self.isy_password,
            )
        self.client_status = "init"
        self.thread = Thread(name='ConnectISY',target=self._connect)
        self.thread.daemon = True
        return self.thread.start()

    def _connect(self):
        listen = True if self.initializing or self.get_listen() == 1 else False
        LOGGER.info("listen={}".format(listen))
        self.initializing = False
        try:
            self.isy_hue_emu.connect(listen)
        except Exception as ex:
            LOGGER.error("PyISY Connection crashed with {}, will restart on next shortPoll".format(ex), exc_info=True)
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
            LOGGER.info('hue_port not defined in customParams, set to default {}'.format(self.hue_port))
            st = False

        default = self.net_ifc['broadcast']
        if 'isy_host' in self.polyConfig['customParams']:
            self.isy_host = self.polyConfig['customParams']['isy_host']
        else:
            self.isy_host = default
        # This can never be the default
        if self.isy_host == default:
            LOGGER.info('isy_host not defined in customParams, set to default {}'.format(default))
            st = False

        default = "80"
        if 'isy_port' in self.polyConfig['customParams']:
            self.isy_port = self.polyConfig['customParams']['isy_port']
        else:
            self.isy_port = default
            LOGGER.info('isy_port not defined in customParams, set to default {}'.format(default))
            st = False

        default = "admin"
        if 'isy_user' in self.polyConfig['customParams']:
            self.isy_user = self.polyConfig['customParams']['isy_user']
        else:
            self.isy_user = default
            LOGGER.info('isy_user not defined in customParams, set to default {}'.format(default))
            st = False

        default = "your_isy_password"
        if 'isy_password' in self.polyConfig['customParams']:
            self.isy_password = self.polyConfig['customParams']['isy_password']
        else:
            self.isy_password = default
        # This can never be the default
        if self.isy_password == default:
            LOGGER.info('isy_password not defined in customParams, set to default {}'.format(default))
            st = False

        # Make sure they are in the params
        self.addCustomParam({'hue_port': self.hue_port, 'isy_host': self.isy_host, 'isy_port': self.isy_port, 'isy_user': self.isy_user, 'isy_password': self.isy_password})

        # Add a notice if some params don't look correct.
        if not st:
            self.addNotice("Please set parameters in configuration page and restart this nodeserver")

    def set_module_logs(self,level):
        logging.getLogger('urllib3').setLevel(level)

    def set_debug_level(self,level):
        LOGGER.info(str(level))
        if level is None:
            level = 20
        level = int(level)
        if level == 0:
            level = 20
        LOGGER.info('Set GV1 to {}'.format(level))
        self.setDriver('GV1', level)
        # 0=All 10=Debug are the same because 0 (NOTSET) doesn't show everything.
        if level <= 10:
            l = logging.DEBUG
        elif level <= 20:
            l = logging.INFO
        elif level <= 30:
            l = logging.WARNING
        elif level <= 40:
            l = logging.ERROR
        elif level <= 50:
            l = logging.CRITICAL
        else:
            LOGGER.error("Unknown level {}".format(level))
            return
        LOGGER.setLevel(l)
        logging.getLogger('hueUpnp').setLevel(l)
        # this is the best way to control logging for modules, so you can
        # still see warnings and errors
        if level < 10:
            self.set_module_logs(logging.DEBUG)
        else:
            # Just warnigns for the modules unless in module debug mode
            self.set_module_logs(logging.WARNING)
        # Or you can do this and you will never see mention of module logging
        #if level < 10:
        #    LOG_HANDLER.set_basic_config(True,logging.DEBUG)
        #else:
        #    # This is the polyinterface default
        #    LOG_HANDLER.set_basic_config(True,logging.WARNING)

    def get_listen(self):
        LOGGER.debug('')
        val = self.getDriver('GV2')
        if val is None:
            val = 1
        LOGGER.debug(val)
        return int(val)

    def set_listen(self,val):
        LOGGER.warning('Set to {}'.format(val))
        if self.isy_hue_emu is not False:
            if val == 0:
                self.isy_hue_emu.stop_listener()
            else:
                self.isy_hue_emu.start_listener()
        self.listen_cnt = HueEmuController.LISTEN_TIMEOUT
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
        LOGGER.info('update_profile','')
        st = self.poly.installprofile()
        return st

    def cmd_refresh(self,command):
        self.refresh()

    def cmd_set_debug_mode(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
        self.set_debug_level(val)

    def cmd_set_listen(self,command):
        val = int(command.get('value'))
        LOGGER.info(val)
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
        {'driver': 'GV2', 'value': 0,  'uom': 2},   # Listen
    ]
