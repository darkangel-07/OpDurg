#!/bin/bash

apt-get update
apt-get install -y wget unzip xvfb libnss3 libgconf-2-4
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt install -y ./google-chrome-stable_current_amd64.deb

# Run script
python3 script.py
