#!/bin/bash -ex

set -ex

sudo apt-get update && apt-get upgrade
sed -i 's/jessie/stretch/g' /etc/apt/sources.list
sudo apt-get update && apt-get upgrade && apt-get dist-upgrade
sudo apt install python3-venv
sed -i 's/python3.4/python3.5/g' _lib/bootstrapping.py
sed -i 's/virtualenv/venv/g' _lib/bootstrapping.py
sudo rm -rf /opt/scotty/src/.env/
systemctl restart scotty-wsgi
read
systemctl restart scotty-celery-worker scotty-celery-beat
