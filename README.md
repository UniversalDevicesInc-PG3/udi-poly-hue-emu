![Build Status](https://travis-ci.org/jimboca/udi-poly-hue-emu.svg?branch=master) master
![Build Status](https://travis-ci.org/jimboca/udi-poly-hue-emu.svg?branch=dev) dev


# udi-poly-hue-emu

This is the Hue Emulator Poly for the [Universal Devices Polisy](https://www.universal-devices.com) [Polyglot interface](http://www.universal-devices.com/developers/polyglot/docs/) with [Polyglot Version 3 (PG3)](https://github.com/UniversalDevicesInc/pg3)

(c) JimBoCA aka Jim Searle
MIT license.

This node server is make it possible to control ISY994 devices from other devices that support a Hue Hub.  So devices like a Harmony Hub can control ISY devices or scenes.  The Harmony Elite remote has dedicated home control buttons which work very well with this setup.  It also should work to control devices with Amazon Alexa, but I no longer use Alexa so I can not support it.  The Google home no longer works with local Hue hubs, so that isn't supported either.

It uses the [PyISY Library](https://pypi.python.org/pypi/PyISY) to connect to the ISY and control devices, and the [Python Hue Hub Emulator](https://github.com/falk0069/hue-upnp) to emulate a Hue Hub.

This version remembers the devices previous hue id so they should not ever change.

## Help

If you have any issues are questions you can ask on [PG3 HueEmulator SubForum](https://forum.universal-devices.com/forum/312-hueemulator/) or report an issue at [PG3 Kasa Github issues](https://github.com/UniversalDevicesInc-PG3/udi-poly-hue-emu/issues).

## Moving from PG2
  
IMPORTANT: 
- If you are upgrading to PG2 first make sure the version you are running on PG2 is 2.2.13 and you have restarted after installing that version.
- Make sure your PG3 version is at least 3.0.38

There are a few ways to move.

### Backup and Restore

The best way to move from PG2 to PG3 is to backup on PG2 and restore on PG3, but the only option is to do all your nodeservers at once.  I don't have much information on this method, if you have questions please ask on the PG3 forum.

### Manual

If you can't or don't want backup/restore then you can delete the NS on PG2 and install on the same slot on PG3.  But, this may result in the devices getting different Hue ID's so you will have to go to any devices that references this emulator and manually fix them.

After it is installed, stop the nodeserver and manually copy the configuration.
  - Log into your Polisy with your prefered terminal program
  - cd /var/polyglot/pg3/ns/uuid_n/config
    - uuid will be your Polsiy UUID
    - n is the slot number for this nodeserver
  - If PG2 is running on your Polisy:
    - sudo -u polyglot cp /var/polyglot/nodeservers/HueEmulator/config/config.json config.json
  - If PG2 is running on another machine
    - sudo -u polyglot scp username@hostname:/var/polyglot/nodeservers/HueEmulator/config/config.json config.json
      - Where username is the username on the machine running PG2
      - and hostname is the host running PG2

### Add then delete

Another option is to install in a new slot then go edit all your programs and scenes that reference the nodes and switch to the new slots. 


## Setup

By default all devices that have a 'Spoken' property set in the ISY notes will be added to the list.  To set this right click on the device in the ISY admin console and select 'Notes'.  If you have a recent version of the ISY firmware and admin console you should see the option to add 'Spoken'.  If you want the spoken name to always match the device name, just make the value of the Spoken property be the number one '1', without the quotes. Make sure there are no accents in the Spoken property, only plain ASCII characters, or the discovery will fail.

To control a scene you can set the Spoken on the scene controller, in which case the server will turn on the scene, or set the Spoken on the scene itself. (Need to test how brighten/dim work with scenes)

The scene status will not always be correct, this is because PyISY decides that a scene is on when any of the devices in the scene is not off.  For this reason I prefer to put the spoken property on the main scene controller I want to track instead of the scene itself.  But if your scene contains multiple responders at different levels this will not work properly.

IMPORTANT: Currently if you 'group device' it will not find your Spoken property on your device.  This is an issue with the PyISY library that I will try to fix soon because almost all my devices were grouped. (Is this still true?)

## Installation

1. Backup Your ISY in case of problems!
   * Really, do the backup, please
2. Go to the Polyglot Store in the UI and install HueEmulator
3. Open the ISY Admin Console, close and re-open if it was already open.
3. Once it installs you should see a new node 'Hue Emulator Controller'
   * If you don't see that node, then restart the node server from the Polyglot UI.
4. Set the Configuration as described in the next section.

## Configuration

The 'Configuration' tab contains the default values for all Custom Configuration Parameters.  It also shows what
devices are found to have spokens.

See [Polyglot Configuration Page](POLYGLOT_CONFIG.md)

### Hue Emulator Controller node

This is the one and only node for this nodeserver.  It has the following options:

* ISY Connected: The status of the process that maintains a connection to the ISY
* Debug Mode:  The Logger mode, debug will spew a lot of information, info is he default.
* Listen:  Enabling this is the same as pushing the button on a hue hub.  You should only turn on when adding the hub to another device.

## Debug

The log for the nodeserver will show that it is parsing all the notes from each device.  When it finds a spoken property it will print information about that device.

You should see it checking the ‘notes’ of each device on the ISY when it starts up:
```2018-06-17 21:05:50,246 INFO     ISY Request: http://your.isy.ip:80/rest/nodes/2E%20AD%2073%201/notes
```

And if it finds a Spoken set you should see:
```2018-06-17 21:05:50,339 INFO     ISYHueEmu:refresh: add_spoken_device: name=The Device Nmae, spoken=The Spoken Property
```
followed by a few other lines about the device.

Also, in the nodeserver directory there will be a config.json that contains the devices it found

## Device Type

The PyISY library currently returns dimmable for some devices that are not dimmable, like the sub buttons of a KPL. We have fixed that specific issue, but if others popup we can add exceptions for them.
If you look on the Polyglot Configuration page for this Node Server you will see a table and in the Hue Type column shows what we use for the Hue device types and currently only support.
  - On/off Light
  - Dimmable Light
So if your device is not being shown correctly then please let me know what the Node address by posting in the Forum [Polyglot V2 Hue Hub Emulator Nodeserver SubForum](https://forum.universal-devices.com/forum/147-polyglot-v2-hue-hub-emulator-nodeserver/) and I may also ask to enable Debug logging mode, restart the node server and send me the log package.

## TODO

- Move device info Custom Configuration Paramaters instead of config.json
- Support scenes as hue scenes?

## Requirements

1. Polyglot V2 itself should be run on Raspian Stretch.
  To check your version, ```cat /etc/os-release``` and the first line should look like
  ```
  PRETTY_NAME=Raspbian GNU/Linux 9 (stretch)
  ```
  It is possible to upgrade from Jessie Stretch, but I would recommend just reimaging the SD card.  Some helpful links:
   * https://www.raspberrypi.org/blog/raspbian-stretch/
   * https://linuxconfig.org/raspbian-gnu-linux-upgrade-from-jessie-to-raspbian-stretch-9
1. This has only been tested with ISY 5.0.12 so it is not guaranteed to work with any other version.

# Upgrading

With PG3 just restarting the nodeserver will do the upgrade if necessary.  But currently this will delete the config file so you must save it first then copy it back:
- sudo -u polyglot cp 00\:21\:b9\:00\:f8\:c8_6/config/config.json .
- Restart NS
- Wait for it to startup 
- Stop it
- sudo -u polyglot cp config.json 00\:21\:b9\:00\:f8\:c8_6/config/
- Start it

# Release Notes

- 3.0.3: 01/10/2022
  - Fix for LOGGER levels
  - Added PG2 upgrade information
- 3.0.2: 01/09/2022
  = First PG3 release, still using PyISY 2.x until PG3 supports 3.x
  - Make sure to restart on PG2 with 2.2.13 before moving to PG3
- 2.2.12: 12/22/2021
  - Upgrade PyISY to 2.1.2 which should fix overloading ISY with open SOAP connections
  - Support PyISY logging level 5 to support https://github.com/automicus/PyISY/issues/200
- 2.2.11: 07/04/2021
  - Fix so listener port could actually be changed
- 2.2.10: 06/25/2021
  - Update pyisy to 2.1.1
- 2.2.9 12/06/2020
  - Fix for arugment change in PyISY 2.1.0
- 2.2.8 09/20/2020
  - Fix bug that kept resetting listen count to 5, even though it wasn't really listening.
- 2.2.6 07/31/2020
  - Fix error in 2.2.5 causing a crash
- 2.2.5 07/31/2020
  - Better fix for https://github.com/jimboca/udi-poly-hue-emu/issues/9 which allows main KPL button to be dimmable, but not the sub buttons
- 2.2.4 07/28/2020
  - https://github.com/jimboca/udi-poly-hue-emu/issues/9
  - See Device Type Section above
- 2.2.3 07/07/2020
  - Fixed reference to dimmable which caused a crash
- 2.2.2 07/08/2020
  - Fix https://github.com/jimboca/udi-poly-hue-emu/issues/8
- 2.2.1 06/22/2020
  - Reorganize code
  - Fix when brightening a device it could wrap around and go back to default on value
  - Update logging levels to control module loggers properly
- 2.2.0 06/10/2020
  - Support for PyISY 2 which is now more robust.  Thanks to @shbatm for the help.
  - Listen turned off after 5 long poll's
  - Listen is on at startup
- 2.1.2 01/21/2020
  - Add driver for ISY Connected status
  - Restart PyISY if it fails https://github.com/jimboca/udi-poly-hue-emu/issues/3
- 2.1.1 11/04/2019
  - Trap and retry for ISY connection failures which occasionally happen on startup when ISY is overloaded
- 2.1.0 11/04/2019
  - Fix get_network_ip to work on Polisy
- 2.0.8 09/03/2019
  - Change to use isy.nodes.nids instead of allLowerNodes
- 2.0.7 03/03/2019
  - No change in this code, but new version due to bug fix in locally cloned hue-upnp code that caused the wrong device to be referenced when items were removed before it from spoken list.
- 2.0.6 08/16/2018
  - Add Heartbeat which sends DON/DOF on each longPoll
- 2.0.5 07/29/2018
  - Add Table of Spoken devices shown in Configuration page, must be on Polyglto 2.2.1
  - Properly track status if ISY devices so proper values show in Harmony
- 2.0.4 07/09/2018
  - Add missing polyinterface to requirements.txt
- 2.0.3 06/21/2018
  - Fix for when a spoken is removed
  - Fix to PyISY for Scenes that contain a nodeserver node
- 2.0.2 06/21/2018
  - Fix initialization of listen
  - Pull my PyISY again to help with debugging
- 2.0.1 06/19/2018
  - Move to released PyISY 1.1.0 to fix finding scenes.
- 2.0.0
  - Never officially released.
