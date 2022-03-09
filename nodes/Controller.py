#!/usr/bin/env python3
"""
This is a NodeServer to Emulate a Hue Hub for Polyglot v2 written in Python3
by JimBo (Jim Searle) jimboca3@gmail.com
"""
from udi_interface import Node,LOGGER,Custom,LOG_HANDLER
import sys
import time
import logging
import pyisy
from ISYHueEmu import ISYHueEmu
from traceback import format_exception
from threading import Thread

class Controller(Node):

    # Number of longPoll calls to timeout listen
    LISTEN_TIMEOUT = 5

    def __init__(self, poly, primary, address, name):
        LOGGER.info('Initializing')
        self.isy_hue_emu = False
        self.restarting  = True
        self.first_run = True
        self.sent_cstr = ""
        self.thread = None
        self.hb = 0
        self.listen_cnt = Controller.LISTEN_TIMEOUT
        self.Notices         = Custom(poly, 'notices')
        self.Params          = Custom(poly, 'customparams')
        poly.subscribe(poly.START,                  self.handler_start, address) 
        poly.subscribe(poly.POLL,                   self.handler_poll)
        poly.subscribe(poly.CONFIGDONE,             self.handler_config_done)
        poly.subscribe(poly.CUSTOMPARAMS,           self.handler_params)
        poly.subscribe(poly.LOGLEVEL,               self.handler_log_level)
        poly.subscribe(poly.STOP,                   self.handler_stop)
        self.handler_start_st      = None
        self.handler_config_st     = None
        self.handler_params_st     = None
        super(Controller, self).__init__(poly, primary, address, name)
        self.Notices.clear()
        poly.ready()
        poly.addNode(self, conn_status="ST")

    def handler_start(self):
        LOGGER.info('Starting')
        self.initializing = True
        LOGGER.info('Version {}'.format(self.poly.serverdata['version']))
        self.net_ifc = self.poly.getNetworkInterface()
        self.heartbeat()
        self.handler_start_st = True
        LOGGER.info('done')

    def handler_config_done(self):
        LOGGER.debug("enter")
        # We listen for new connections on restart...
        self.set_isy_connected(False)
        self.poly.addLogLevel('DEBUG_MODULES',5,'Debug + Verbose Modules')
        self.poly.addLogLevel('DEBUG_MODULES_VERBOSE',9,'Debug + Modules')
        # This is supposed to only run after we have received and
        # processed all config data, just add a check here.
        cnt = 60
        while ((self.handler_start_st is None
            or self.handler_params_st is None)
            and cnt > 0
        ):
            LOGGER.warning(f'Waiting for all handlers to complete start={self.handler_start_st} params={self.handler_params_st} cnt={cnt}')
            time.sleep(1)
            cnt -= 1
        if cnt == 0:
            LOGGER.error('Timed out waiting for all handlers to complete')
            self.poly.stop()
            return
        if self.handler_params_st:
            self.connect()
        else:
            LOGGER.error(f'Unable to start REST Server until config params are correctd ({self.handler_params_st})')
        self.handler_config_st = True
        self.first_run = False
        LOGGER.debug("exit")

    def handler_poll(self, polltype):
        if self.restarting:
            LOGGER.warning("no polling when restarting...")
            return
        if polltype == 'longPoll':
            self.longPoll()
        else:
            self.shortPoll()

    def shortPoll(self):
        self.update_config_docs()
        if self.thread is not None:
            if not self.thread.is_alive():
                self.thread = None
                LOGGER.error("Thread is dead, restarting.")
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
        self.stop_thread()
        LOGGER.info('Oh God I\'m being deleted. Nooooooooooooooooooooooooooooooooooooooooo.')

    def handler_stop(self):
        LOGGER.info("Stopping")
        self.stop_thread()
        LOGGER.info('NodeServer stopped.')

    def refresh(self, *args, **kwargs):
        LOGGER.info('')
        if self.isy_hue_emu is False:
            LOGGER.error('No Hue Emulator?')
            return
        self.isy_hue_emu.refresh()
        self.update_config_docs()

    def update_config_docs(self):
        # '<style> table { cellpadding: 10px } </style>'
        self.config_info = [
        '<h1>Spoken Device Table</h1>',
        'This table is refreshed during short poll, so it may be out of date for a few seconds<br>',
        '<table border=1>',
        '<tr><th colspan=2><center>Hue<th rowspan=2><center>NSId<th colspan=2><center>Property Node/Scene<th colspan=3><center>Scene<th rowspan=2><center>Spoken<th rowspan=2><center>On<th rowspan=2><center>Bri</tr>',
        '<tr><th><center>Id<th><center>Type<th><center>Id<th><center>NodeDefId<th><center>Name<th><center>Scene<th><center>Name<th></tr>']
        if self.isy_hue_emu is not False:
            for i, device in enumerate(self.isy_hue_emu.pdevices):
                # Only used for debug
                if device is False:
                    dtype = 'None'
                elif device.node.protocol == pyisy.constants.PROTO_GROUP:
                    dtype = 'Scene'
                else:
                    dtype = device.node.node_def_id
                if device is False:
                    self.config_info.append('<tr><td>{}<td colspan=9>empty</tr>'.format(i))
                elif device.scene is False:
                    self.config_info.append('<tr><td>{}<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td colspan=2>&nbsp;None&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;</tr>'.
                    format(i,device.type,device.id,device.node,dtype,device.node.name,device.name,device.on,device.bri))
                else:
                    self.config_info.append('<tr><td>&nbsp;{}&nbsp;<td>{}<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;<td>&nbsp;{}&nbsp;</tr>'.
                    format(i,device.type,device.id,device.node,dtype,device.node.name,device.scene,device.scene.name,device.name,device.on,device.bri))
        self.config_info.append('</table>')
        s = "\n"
        #
        # Set the Custom Config Doc when it changes
        #
        cstr = s.join(self.config_info)
        if self.sent_cstr != cstr:
            self.poly.setCustomParamsDoc(cstr)
            self.sent_cstr = cstr

    def stop_thread(self):
        if self.thread is not None and self.thread.is_alive():
            LOGGER.info('Stopping current thread for ISYHueEmu')
           # Must kill the existing thread
            self.isy_hue_emu.stop()

    def connect(self):
        LOGGER.debug("enter")
        self.restarting = True
        self.stop_thread()

        LOGGER.info('Starting thread for ISYHueEmu')
        self.restarting = False

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
        self.set_listen(1 if listen else 0)
        LOGGER.info("listen={}".format(listen))
        self.initializing = False
        try:
            self.set_isy_connected(True)
            self.isy_hue_emu.connect(listen)
        except Exception as ex:
            LOGGER.error("PyISY Connection crashed with {}, will restart on next shortPoll".format(ex), exc_info=True)
        # Thread is dead?
        self.set_isy_connected(False)

    def handler_params(self, data):
        LOGGER.debug("Enter data={}".format(data))
        self.Params.load(data)
        # Assume we are good unless something bad is found
        st = True

        params = {
            'hue_port': '8081',
            'isy_host': "your_isy_host_or_ipaddress",
            'isy_port': '8080',
            'isy_user': 'admin',
            'isy_password': 'your_isy_admin_user_password'
        }
        # Make sure all the params exist.
        for param in params:
            if not param in data:
                LOGGER.error(f'Add back missing param {param}')
                self.Params[param] = params[param]
                # Can't do anything else because we will be called again due to param change
                return
        # Make sure they all have a value
        for param in params:
            if data[param] == "" or ((param == 'isy_host' or param == 'isy_password') and data[param] == params[param]):
                msg = f'Please define {param}'
                LOGGER.error(msg)
                self.Notices[param] = msg
                st = False
            else:
                self.Notices.delete(param)

        self.hue_port = data['hue_port']
        self.isy_host = data['isy_host']
        self.isy_port = data['isy_port']
        self.isy_user = data['isy_user']
        self.isy_password = data['isy_password']

        # Don't call connect on first run, handler_config_done will doe it
        if not self.first_run:
            self.connect()

        self.handler_params_st = st

    def handler_log_level(self,level):
        LOGGER.info(f'enter: level={level}')
        if level['level'] < 10:
            LOGGER.info("Setting basic config to DEBUG...")
            LOG_HANDLER.set_basic_config(True,logging.DEBUG)
        else:
            LOGGER.info("Setting basic config to WARNING...")
            LOG_HANDLER.set_basic_config(True,logging.WARNING)
        # Always use the requested level for these two
        logging.getLogger('hueUpnp').setLevel(level['level'])
        logging.getLogger('ISYHueEmu').setLevel(level['level'])
        LOGGER.info(f'exit:')

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
                self.listen_cnt = Controller.LISTEN_TIMEOUT
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
        LOGGER.info('update_profile')
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
        {'driver': 'ST',  'value': 1,  'uom': 25},   # Node Status
        {'driver': 'GV0', 'value': 0,  'uom': 2},   # ISY Connected
        {'driver': 'GV2', 'value': 0,  'uom': 2},   # Listen
    ]
