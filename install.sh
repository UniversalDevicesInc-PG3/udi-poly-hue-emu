#!/usr/bin/env bash

pip3 install -r requirements.txt --user

echo ""
if [ -e PyISY ]; then
  echo "Removing: PyISY"
  rm -rf PyISY
fi
git clone https://github.com/jimboca/PyISY

echo ""
if [ -e hue-upnp ]; then
  echo "Removing: hue-upnp"
  rm -rf hue-upnp
fi
git clone https://github.com/jimboca/hue-upnp
