#
# The ISYHueEmu object.
#
# It is contained in a seperate object because the intention was to allow running
# just this file to test, but haven't done that yet...
#

import json,os

import sys
import re
import pyisy
import shutil
import logging

# Local version of hue-upnp which works with Python3
sys.path.insert(0,"hue-upnp")
from hueUpnp import hue_upnp,hue_upnp_super_handler
# This loads the default hue-upnp config which we will use as a starting point.
import hueUpnp_config

LOGGER = logging.getLogger(__name__)

class ISYHueEmu():

    config_version = 1

    def __init__(self,host,port,isy_host,isy_port,isy_user,isy_password):
        self.host         = host
        self.port         = port
        self.isy          = None # The pyisy.ISY object
        self.isy_host     = isy_host
        self.isy_port     = isy_port
        self.isy_user     = isy_user
        self.isy_password = isy_password
        self.pdevices  = []
        self.lpfx = 'pyhue:'
        self.listening = False
        self.config_file = 'config.json'
        self.hue_upnp     = False
        self.load_config()

    def isy_connected(self):
        if self.isy is None:
            return False
        return self.isy.connected

    def connect(self,listen):
        done = False
        cnt  = 0
        while (not done):
            cnt += 1
            LOGGER.debug('ISY connect try %d' % (cnt))
            try:
                self.isy = pyisy.ISY(self.isy_host, self.isy_port, self.isy_user, self.isy_password, False, 1.1, "")
                done = True
            except Exception as ex:
                # Can any other exception happen?
                template = "An exception of type {0} occured. Arguments:\n{1!r}"
                message = template.format(type(ex).__name__, ex.args)
                LOGGER.error(message, exc_info=True)
            LOGGER.info(' ISY Connected: ' + str(self.isy.connected))
            if not self.isy.connected:
                if cnt == 10:
                    LOGGER.error('Tried to connect 10 times, giving up')
                    done = True
                else:
                    LOGGER.error('ISY not connected, will try again')

        if not self.isy.connected:
            return False
        # Now that we are all setup, we can accept device changes from the isy.
        # FIXME: But this means from the time we connect till now, we can miss
        # FIXME: device status changes, do we care?
        self.isy.auto_update = True
        if not self.refresh():
            return False
        #
        # Now start up the hue_upnp...
        #
        LOGGER.info('Default config: {}'.format(hueUpnp_config))
        hueUpnp_config.devices = self.pdevices
        hueUpnp_config.standard['IP']        = self.host
        hueUpnp_config.standard['PORT']      = self.port
        hueUpnp_config.standard['DEBUG']     = True
        self.hue_upnp = hue_upnp(hueUpnp_config)
        self.listening = listen
        self.hue_upnp.run(listen=listen)

    def start_listener(self):
        if self.hue_upnp is not False:
            self.hue_upnp.start_listener()

    def stop_listener(self):
        if self.hue_upnp is not False:
            self.hue_upnp.stop_listener()

    def save_config(self):
        LOGGER.info(self.config_file)
        self.config['version'] = 1
        # Only used for debugging
        self.config['devices_hue'] = []
        self.config_info = []
        for i, device in enumerate(self.pdevices):
            # Only used for debug
            if device is False:
                self.config['devices_hue'].append(device)
                self.config_info.append('device index={} empty'.format(i))
            else:
                self.config['devices_hue'].append({'name': device.name, 'id': device.id, 'index': i })
                self.config_info.append('device index={} id={} name={}'.format(i,device.id,device.name))
        LOGGER.info("saving config.tmp")
        with open("config.tmp", 'w') as outfile:
            json.dump(self.config, outfile, ensure_ascii=False, indent=4, sort_keys=True)
        LOGGER.info("saving {}".format(self.config_file))
        os.rename("config.tmp",self.config_file)

    def load_config(self):
        if os.path.exists(self.config_file):
            LOGGER.info(self.config_file)
            with open(self.config_file, "r") as ifile:
                self.config = json.load(ifile)
        else:
            LOGGER.info('No config, using default')
            self.config = { 'devices': [], 'config': hueUpnp_config.standard, 'version': 1 }

    def refresh(self):
        errors = 0
        # Build device list for emulator full of False which are ignored by hue-Upnp
        # This is so remvoed devices are just blanks
        max = -1
        for item in self.config['devices']:
            if item['index'] > max:
                max = item['index']
        LOGGER.info('max index = {}'.format(max))
        self.pdevices = []
        for i in range(0,max+1):
            self.pdevices.append(False)
        LOGGER.info('max index = {}, len pdevices = {}'.format(max,len(self.pdevices)))
        found_nodes = False
        for (_, child) in self.isy.nodes:
            ctype = type(child).__name__
            LOGGER.info("add_spoken_device: checking {} type={} ctype={}".format(child,type(child),ctype))
            found_nodes = True
            if ctype in ['Node', 'Group']:
                #LOGGER.info(child)
                mnode = child
                spoken = mnode.spoken
                if spoken is not None:
                    # TODO: Should this be a comma seperatd list of which echo will respond?
                    # TODO: Or should that be part of notes?
                    if spoken == '1':
                        spoken = mnode.name
                    LOGGER.info("add_spoken_device: name=" + mnode.name + ", spoken=" + str(spoken))
                    cnode = False
                    if ctype == "Node":
                        # Is it a controller of a scene?
                        cgroup = mnode.get_groups(responder=False)
                        if len(cgroup) > 0:
                            cnode = self.isy.nodes[cgroup[0]]
                            LOGGER.info(" is a scene controller of " + str(cgroup[0]) + '=' + str(cnode) + ' "' + cnode.name + '"')
                    else:
                        cnode = mnode
                        #if len(mnode.controllers) > 0:
                        # FIXME: Problem with this is it may pick the wrong controller
                        # FIXME: If a remotelink and kpl are both controllers may pick the remotelink :(
                        #        mnode = self.isy.nodes[mnode.controllers[0]]
                    self.insert_device(pyhue_isy_node_handler(self,spoken,mnode,cnode))
        if not found_nodes:
            LOGGER.error("No nodes with spoken found, could have been an ISY connection error?")
            return;
        self.save_config()


        #for var in self.isy.variables.children:
        #        # var is a tuple of type, name, number
        #        # TODO: Use ([^\/]+) instead of (.*) ?
        #        match_obj = re.match( r'.*\.Spoken\.(.*)', var[1], re.I)
        #        if match_obj:
        #                var_obj = self.parent.isy.variables[var[0]][var[2]]
        #                self.insert_device(pyhue_isy_var_handler(self,match_obj.group(1),var))

        #errors += 1
        if errors > 0:
            raise ValueError("See Log")
        return True

    def in_config(self,device):
        # Config devices saves the id and name so we can keep the same index.
        for item in self.config['devices']:
            if device.id == item['id']:
                LOGGER.info('Found id in config {}'.format(item))
                return item
        # Didn't find by id, try by name
        for item in self.config['devices']:
            if device.name == item['name']:
                LOGGER.info('Found name in config {}'.format(item))
                return item
        return False

    def insert_device(self,device):
        # TODO: See if we have an id with this name and use it
	    # TODO: This is so ID's never change.
        fdev = self.in_config(device)
        if fdev is False:
            LOGGER.info('Appending device name={} id={} index={}'.format(device.name,device.id,len(self.pdevices)))
            self.config['devices'].append({'name': device.name, 'id': device.id, 'index': len(self.pdevices), 'type': device.type })
            self.pdevices.append(device)
        else:
            #This shouldn't happen now that we initialize the list with False
            #for value in variable}if len(self.pdevices) <= fdev['index']:
            #    LOGGER.info('Inserting device name={} id={} index={}'.format(device.name,device.id,fdev['index']))
            #    self.pdevices.insert(fdev['index'],device)
            #else:
            LOGGER.info('Setting   device name={} type={} id={} index={} '.format(device.name,device.type,device.id,fdev['index']))
            self.pdevices[fdev['index']] = device


    def xxx_add_device(self,config):
        LOGGER.info(str(config))
        if not 'name' in config:
            raise ValueError("No name defined for " + str(config))
        if not 'type' in config:
            config['type'] = 'ISY'
        if config['type'] == 'ISY':
            #node = self.isy.nodes['Family Room Table']
            dname = config['name']
            if 'address' in config:
                dname = str(config['address'])
            try:
                node = self.isy.nodes[dname]
            except:
                node = self.get_isy_node_by_basename(dname)
            if node is None:
                raise ValueError("Unknown device name or address '" + dname + "'")
            else:
                self.insert_device([ config['name'], device_isy_onoff(self,node)])

        else:
            raise ValueError("Unknown PyHue device type " + config['type'])

#
# This is the hue_upnp object for an ISY device
#
class pyhue_isy_node_handler(hue_upnp_super_handler):
        global CONFIG

        def __init__(self, parent, name, node, scene):
                self.name    = name
                self.parent  = parent
                self.node    = node
                # Used to look for device in list in case name changes.
                self.id      = node.address
                self.scene   = scene
                self.dimmable = False
                self.is_scene = False
                self.set_scene = False
                # Matchs KPL buttons except the main one, since that is dimmable and the others are not.
                kpl_sub = re.compile('^[0-9A-F]{2}\s[0-9A-F]{2}\s[0-9A-F]{2}\s[2-9]+')
                # By default we control the main node, which can be a scene
                self.control_device = self.node
                if node.protocol == pyisy.constants.PROTO_GROUP:
                    LOGGER.info('name=%s node=%s scene=%s protocol=%s' % (self.name, self.node, self.scene, node.protocol))
                    # TODO: Should this be a Hue Scene?
                    # We assume scenes are dimmable, although we don't handle this properly yet...
                    self.type = "Dimmable light"
                    self.is_scene = True
                    self.set_scene = True
                else:
                    LOGGER.info('name=%s node=%s node.type=%s node.dimmable=%s scene=%s protocol=%s' % (self.name, self.node, self.node.type, self.node.dimmable, self.scene, node.protocol))
                    if node.dimmable is True:
                        # Not All KPL buttons!
                        match = kpl_sub.match(self.node.address)
                        LOGGER.info('kpl_sub {} match={}'.format(self.node.address,match))
                        if match is None:
                            self.type = "Dimmable light"
                            self.dimmable = True
                        else:
                            self.type = "On/off light"
                    else:
                        self.type = "On/off light"
                    # These node types can not be directly controled, so control the scene
                    # nodeDefId="KeypadButton_ADV"
                    #if node.type == '1.66.69.0':
                    #if node.node_def_id == "KeypadButton_ADV" or node.node_def_id == "RelayLampSwitch_ADV":
                    #    self.control_device = self.scene
                    #    self.set_scene = True
                    #    self.type = "On/off Light"
                self.xy      = False
                self.ct      = False
                self.bri     = 0
                self.on      = "false"
                node.status_events.subscribe(self.get_all_changed)
                LOGGER.info('name=%s node=%s scene=%s type=%s dimmable=%s' % (self.name, self.node, self.scene, self.type, self.dimmable))
                super(pyhue_isy_node_handler,self).__init__(name)

        def get_all_changed(self,e):
                LOGGER.info('%s e=%s' % (self.name, str(e)));
                self.get_all()

        def get_all(self):
                LOGGER.info('%s status=%s' % (self.name, self.node.status))
                # Set all the defaults
                super(pyhue_isy_node_handler,self).get_all()
                # node.status will be 0-255
                if self.node.status == pyisy.constants.ISY_VALUE_UNKNOWN:
                    LOGGER.warning('%s status=%s, changing to 0' % (self.name, self.node.status));
                    self.bri = 0
                else:
                    # TODO: if it's a scene, calculate the on level?
                    self.bri = int(self.node.status)
                if int(self.bri) == 0:
                    self.on  = "false"
                else:
                    self.on  = "true"
                LOGGER.info('%s on=%s bri=%s' % (self.name, self.on, str(self.bri)));

        def set_on(self):
                LOGGER.info('%s node.turn_on()' % (self.name));
                if self.scene != False:
                        ret = self.scene.turn_on()
                        LOGGER.info('%s scene.turn_on() = %s' % (self.name, str(ret)));
                else:
                        # TODO: If the node is a KPL button, we can't control it, which shows an error.
                        ret = self.node.turn_on()
                        LOGGER.info('%s node.turn_on() = %s' % (self.name, str(ret)));
                return ret

        def set_off(self):
                LOGGER.info('%s node.turn_off()' % (self.name));
                if self.scene != False:
                        ret = self.scene.turn_off()
                        LOGGER.info('%s scene.turn_off() = %s' % (self.name, str(ret)));
                else:
                        # TODO: If the node is a KPL button, we can't control it, which shows an error.
                        ret = self.node.turn_off()
                return ret

        def set_bri(self,value):
                LOGGER.info('{} on val={} dimmable={}'.format(self.name, value, self.dimmable));
                # Only set directly on the node when it's dimmable and value is not 0 or 255
                # 06/21/2020: changed to allow passing 255 value.
                # TODO: But should we also check if dimmable?
                if value > 0:
                        if self.set_scene:
                            LOGGER.info('{} node.set_on()'.format(self.name));
                            ret = self.set_on()
                            # TODO: Calculat brightness from scene members?
                            self.bri = 255
                        else:
                            if self.dimmable:
                                # val=bri does not work?
                                ret = self.node.turn_on(value)
                            else:
                                # val > 254, so just turn on.  This fixes defines that are not dimmable
                                # like kpl buttons which can't be controlled directly.
                                LOGGER.info('{} node.set_on()'.format(self.name));
                                ret = self.set_on()
                            LOGGER.info('{} node.turn_on({}) = {}'.format(self.name, value, ret));
                else:
                        ret = self.set_off()
                        self.bri = 0
                LOGGER.info('{} on={} bri={}'.format(self.name, self.on, self.bri));
                return ret

# TODO: Somday support setting ISY variables?
#class pyhue_isy_var_handler(hue_upnp_super_handler):
#        def __init__(self, parent, name, var):
#                self.parent  = parent
#                self.name    = name
#                self.var     = var
#                self.update()
#                #node.subscribe('changed', partial(self.update))
#                self.handler = var.val.subscribe('changed', partial(self.update))
#                super(isy_rest_handler,self).__init__(name)
#
#        def update(self):
#                # TODO: if var.on is true?
#                if self.var.val == 0:
#                        self.on  = "false"
#                        self.bri = 0
#                else:
#                        self.on  = "true"
#                        self.bri = self.var.val
#                self.xy  = [0.0,0.0];
#                self.ct  = 0
#
#        def set(self,data):
#                ret = False
#                self.parent.parent.logger.info('pyhue:var_handler.set:  ' + str(data));
#                if 'bri' in data:
#                        bri = str(data['bri'])
#                        self.parent.parent.logger.info('pyhue:isy_handler.set: on val=' + bri);
#                        # val=bri does not work?
#                        ret = self.var.val(bri)
#                        if ret:
#                                self.on = "true"
#                                self.bri = bri
#                elif 'on' in data:
#                        if data['on']:
#                                ret = self.var.val(1)
#                                if ret:
#                                        self.on = "true"
#                        else:
#                                ret = self.var.val(0)
#                                if ret:
#                                        self.on = "false"
#                return ret
