#!/usr/bin/env bash

if [  $# -gt 0 ]; then
  echo "Skipping pip3 install, must be a travis run?"
else
  pip3 install -r requirements.txt --user
fi

echo ""
if [ -e PyISY ]; then
  echo "Removing: PyISY since we can use the released version now"
  rm -rf PyISY
fi
# We can use the released 1.1.0 version now.
# But mine is the same with additional debugging
git clone https://github.com/jimboca/PyISY.git

echo ""
if [ -e hue-upnp ]; then
  echo "Removing: hue-upnp"
  rm -rf hue-upnp
fi
git clone -b python3 https://github.com/jimboca/hue-upnp.git
