#!/bin/bash -ex


sudo apt-get update && apt-get upgrade
sed -i 's/jessie/stretch/g' /etc/apt/sources.list
sudo apt-get update && apt-get upgrade && apt-get dist-upgrade
sed -i 's/python2.7/python3.5/g' _lib/bootstrapping.py
sed -i 's/virtualenv/venv/g' _lib/bootstrapping.py
sudo rm -rf /apt/scotty/src/.env/
systemctl restart scotty-wsgi
sudo apt install python3-venv
systemctl restart scotty-celery-worker scotty-celery-beat
