

import socket,json

def get_network_interface(interface='default',logger=None):
    # Get the default gateway
    gws = netifaces.gateways()
    rt = False
    if interface in gws:
        gwd = gws[interface][netifaces.AF_INET]
        logger.debug("gwd: {}={}".format(interface,gwd))
        ifad = netifaces.ifaddresses(gwd[1])
        rt = ifad[netifaces.AF_INET]
        logger.debug("ifad: {}={}".format(gwd[1],rt))
    else:
        logger.error("No {} in gateways:{}".format(interface,gateways))
    return rt


def get_network_ip(logger=None):
    try:
        iface = get_network_interface(logger=logger)
        rt = iface[0]['addr']
    except Exception as err:
        logger.error('get_network_ip: failed: {0}'.format(err))
        rt = False
    logger.info('get_network_ip: Returning {0}'.format(rt))
    return rt

def get_server_data(logger):
    # Read the SERVER info from the json.
    try:
        with open('server.json') as data:
            serverdata = json.load(data)
    except Exception as err:
        logger.error('hue_emu_funcs:get_server_data: failed to read and parse file {0}: {1}'.format('server.json',err), exc_info=True)
        return False
    data.close()
    # Get the version info
    try:
        version = serverdata['credits'][0]['version']
    except (KeyError, ValueError):
        logger.info('hue_emu_funcs: Version not found in server.json.')
        version = '0.0.0.0'
    # Split version into two floats.
    sv = version.split(".");
    v1 = 0;
    v2 = 0;
    if len(sv) == 1:
        v1 = int(v1[0])
    elif len(sv) > 1:
        v1 = float("%s.%s" % (sv[0],str(sv[1])))
        if len(sv) == 3:
            v2 = int(sv[2])
        else:
            v2 = float("%s.%s" % (sv[2],str(sv[3])))
    serverdata['version'] = version
    serverdata['version_major'] = v1
    serverdata['version_minor'] = v2
    return serverdata
