#
# The ISYHueEmulator object.
#
# It is contained in a seperate object because the intention was to allow running
# just this file to test, but haven't done that yet...
#

import json,os

# Local version of PyISY which supports ISY 5.x
import sys
sys.path.insert(0,"PyISY")
import PyISY

# Local version of hue-upnp which works with Python3
sys.path.insert(0,"hue-upnp")
from hueUpnp import hue_upnp,hue_upnp_super_handler
# This loads the default hue-upnp config which we will use as a starting point.
import hueUpnp_config

import polyinterface
LOGGER = polyinterface.LOGGER

class ISYHueEmulator():
    def __init__(self,host,port,isy_host,isy_port,isy_user,isy_password):
        self.host         = host
        self.port         = port
        self.isy_host     = isy_host
        self.isy_port     = isy_port
        self.isy_user     = isy_user
        self.isy_password = isy_password
        self.pdevices  = []
        self.lpfx = 'pyhue:'
        self.listening = False
        self.config_file = 'config.json'
        self.load_config()

    def connect(self):
        # FIXME: How to set different logger level for Events?
        self.isy = PyISY.ISY(self.isy_host, self.isy_port, self.isy_user, self.isy_password, False, "1.1", LOGGER)
        self.l_info('connect',' ISY Connected: ' + str(self.isy.connected))
        if not self.isy.connected:
            return False
        if not self.refresh():
            return False
        self.l_info('connect','Default config: {}'.format(hueUpnp_config))
        hueUpnp_config.devices = self.pdevices
        hueUpnp_config.logger  = LOGGER
        hueUpnp_config.standard['IP']        = self.host
        hueUpnp_config.standard['PORT']      = self.port
        hueUpnp_config.standard['DEBUG']     = True
        self.hue_upnp = hue_upnp(hueUpnp_config)
        self.save_config()
        self.hue_upnp.run()
        self.listening = True
        #self.isy.auto_update = True

    __config_version = 1

    def save_config(self):
        new_config = { 'devices': {}, 'config': hueUpnp_config.standard, 'version': __config_version }
        for i, device in enumerate(self.pdevices):
            fdev = self.in_config(device)
            if fdev is False:
                new_config['devices'].append({'name': device.name, 'id': device.id, 'index': i })
        self.config = new_config
        with open(self.config_file, 'w') as outfile:
            json.dump(self.config, outfile, ensure_ascii=False, indent=4, sort_keys=True)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as ifile:
                self.config = json.load(read_file)
        else:
            self.config = { 'devices': {}, 'config': hueUpnp_config.standard, 'version': __config_version }

    def refresh(self):
        errors = 0
        lpfx = 'refresh'
        for child in self.isy.nodes.allLowerNodes:
            if child[0] is 'node' or child[0] is 'group':
                #self.l_info(lpfx,child)
                mnode = self.isy.nodes[child[2]]
                spoken = mnode.spoken
                if spoken is not None:
                    # TODO: Should this be a comma seperatd list of which echo will respond?
                    # TODO: Or should that be part of notes?
                    if spoken == '1':
                        spoken = mnode.name
                    self.l_info(lpfx,"add_spoken_device: name=" + mnode.name + ", spoken=" + str(spoken))
                    cnode = False
                    if child[0] is 'node':
                        # Is it a controller of a scene?
                        cgroup = mnode.get_groups(responder=False)
                        if len(cgroup) > 0:
                            cnode = self.isy.nodes[cgroup[0]]
                            self.l_info(lpfx," is a scene controller of " + str(cgroup[0]) + '=' + str(cnode) + ' "' + cnode.name + '"')
                    else:
                        cnode = mnode
                        if len(mnode.controllers) > 0:
                                mnode = self.isy.nodes[mnode.controllers[0]]
                    self.insert_device(pyhue_isy_node_handler(self,spoken,mnode,cnode))


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
            if device['id'] == item['id']:
                self.l_info('in_config','Found id in config {}'.format(item))
                return item
        # Didn't find by id, try by name
        for item in self.config['devices']:
            if device['name'] == item['name']:
                self.l_info('in_config','Found name in config {}'.format(item))
                return item
        return False

    def insert_device(self,device):
        # TODO: See if we have an id with this name and use it
	    # TODO: This is so ID's never change.
        fdev = self.in_config(device)
        if fdev is False:
            self.l_info('insert_device','Appending device name={} id={} index={}'.format(device.name,device.id,len(self.pdevices)))
            self.pdevices.append(device)
        else:
            self.l_info('insert_device','Inserting device name={} id={} index={}'.format(device.name,device.id,index))
            self.pdevices.insert(index,device)

    def add_device(self,config):
        self.l_info('add_device',str(config))
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


    def l_info(self, name, string):
        LOGGER.info("ISYHueEmu:%s: %s" %  (name,string))

    def l_error(self, name, string, exc_info=False):
        LOGGER.error("ISYHueEmu:%s: %s" % (name,string), exc_info=exc_info)

    def l_warning(self, name, string):
        LOGGER.warning("ISYHueEmu:%s: %s" % (name,string))

    def l_debug(self, name, string):
        LOGGER.debug("ISYHueEmu:%s: %s" % (name,string))

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
                self.id      = node.id
                self.scene   = scene
                self.xy      = False
                self.ct      = False
                node.status.subscribe('changed', self.get_all_changed)
                self.parent.l_info('pyhue_isy_node_handler.__init__','name=%s node=%s scene=%s' % (self.name, self.node, self.scene));
                super(pyhue_isy_node_handler,self).__init__(name)

        def get_all_changed(self,e):
                self.parent.l_info('pyhue:isy_node_handler.get_all_changed','%s e=%s' % (self.name, str(e)));
                self.get_all()

        def get_all(self):
                self.parent.l_info('pyhue:isy_node_handler.get_all','%s status=%s' % (self.name, str(self.node.status)));
                # Set all the defaults
                super(pyhue_isy_node_handler,self).get_all()
                # node.status will be 0-255
                self.bri = self.node.status
                if int(self.node.status) == 0:
                        self.on  = "false"
                else:
                        self.on  = "true"
                self.parent.l_info('pyhue:isy_node_handler.get_all','%s on=%s bri=%s' % (self.name, self.on, str(self.bri)));

        def set_on(self):
                self.parent.l_info('pyhue:isy_handler.set_on','%s node.on()' % (self.name));
                if self.scene != False:
                        ret = self.scene.on()
                        self.parent.l_info('pyhue:isy_handler.set_on','%s scene.on() = %s' % (self.name, str(ret)));
                else:
                        # TODO: If the node is a KPL button, we can't control it, which shows an error.
                        ret = self.node.on()
                return ret

        def set_off(self):
                self.parent.l_info('pyhue:isy_handler.set_off','%s node.off()' % (self.name));
                if self.scene != False:
                        ret = self.scene.off()
                        self.parent.l_info('pyhue:isy_handler.set_off','%s scene.off() = %s' % (self.name, str(ret)));
                else:
                        # TODO: If the node is a KPL button, we can't control it, which shows an error.
                        ret = self.node.off()
                return ret

        def set_bri(self,value):
                self.parent.l_info('pyhue:isy_handler.set_bri','%s on val=%d' % (self.name, value));
                # Only set directly on the node when it's dimmable and value is not 0 or 254
		        # TODO: node.dimmable broken in current PyISY?
                if value > 0 and value < 254:
                        # val=bri does not work?
                        ret = self.node.on(value)
                        self.parent.l_info('pyhue:isy_handler.set_bri','%s node.on(%d) = %s' % (self.name, value, str(ret)));
                else:
                        if value > 0:
                                ret = self.set_on()
                                self.bri = 255
                        else:
                                ret = self.set_off()
                                self.bri = 0
                self.parent.l_info('pyhue:isy_handler.set_bri','%s on=%s bri=%d' % (self.name, self.on, self.bri));
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
