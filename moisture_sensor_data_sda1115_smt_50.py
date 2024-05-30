# !/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import json  # for working with data file
from threading import Thread
from time import sleep

# local module imports
from blinker import signal
import time
import gv  # Get access to SIP's settings
import os
from smbus2 import SMBus

# ADS1115 + hardware constants
I2C_BUS = 1
POINTER_CONVERSION = 0x0
POINTER_CONFIGURATION = 0x1

RESET_ADDRESS = 0b0000000
RESET_COMMAND = 0b00000110
# END ADS1115 + hardware constants

SENSOR_DATA_PATH = "./static/data/moisture_sensor_data"

# Settings - ToDo make configurable
SENSOR_NAME = "sda1115_smt_50"
SENSOR_DEVICE_ADDRESS = 0x48
SENSOR_READ_INTERVALL_MINUTES = 5
SENSOR_MAX_VOLTAGE = 3
SENSOR_DRIEST = 0
SENSOR_WETTEST = 50
SENSOR_CHANNEL = 0

msd_signal = signal("moisture_sensor_data")

def moisture_sensor_data_init():
    if not os.path.isdir(SENSOR_DATA_PATH):
        os.makedirs(SENSOR_DATA_PATH, exist_ok=True)

    sensor_file = f"{SENSOR_DATA_PATH}/{SENSOR_NAME}"
    if not os.path.isfile(sensor_file):
        create_sensor_data_file(sensor_file)

def create_sensor_data_file(new_file):
    """Use x and y as headings for the graph plugin"""
    with open(new_file, "w") as f:
        f.write("x,y\n")

#ADS1115 functions
def prepareLEconf(BEconf):
    '''Prepare LittleEndian Byte pattern from BigEndian configuration string, with separators.'''
    c = int(BEconf.replace('-', ''), base=2)
    return swap2Bytes(c)

def swap2Bytes(c):
    '''Revert Byte order for Words (2 Bytes, 16 Bit).'''
    return (c >> 8 | c << 8) & 0xFFFF

def LEtoBE(c):
    '''Little Endian to BigEndian conversion for signed 2Byte integers (2 complement).'''
    c = swap2Bytes(c)
    if (c >= 2 ** 15):
        c = c - 2 ** 16
    return c

def read_channel():
    bus = SMBus(I2C_BUS)
    bus.write_byte(RESET_ADDRESS, RESET_COMMAND)
    # compare with configuration settings from ADS115 datasheet
    # start single conversion - AIN0/GND - 4.096V - single shot - 8SPS - X
    # - X - X - disable comparator
    conf = prepareLEconf('1-100-001-1-000-0-0-0-11')
    bus.write_word_data(SENSOR_DEVICE_ADDRESS, POINTER_CONFIGURATION, conf)
    # long enough to be safe that data acquisition (conversion) has completed
    time.sleep(1)
    value_raw = bus.read_word_data(SENSOR_DEVICE_ADDRESS, POINTER_CONVERSION)
    bus.close()
    value = LEtoBE(value_raw)
    voltage = value / pow(2,15) * 4.096
    return voltage
#END ADS1115 functions

def read_loop():
    while True:
        ts_secs = int(gv.now)
        currentVoltage = read_channel()
        percent = currentVoltage / SENSOR_MAX_VOLTAGE * 100 / 2
        percent = round(percent)
        msd_signal.send(
            "reading", data={"sensor": SENSOR_NAME, "timestamp": ts_secs, "value": percent}
        )
        sensor_file = f"{SENSOR_DATA_PATH}/{SENSOR_NAME}"
        with open(sensor_file, "a") as f:
            f.write(f"{ts_secs * 1000},{percent}\n")
        time.sleep(60 * SENSOR_READ_INTERVALL_MINUTES)

moisture_sensor_data_init()

# Run data_test() in baskground thread
readLoop = Thread(target = read_loop)
readLoop.daemon = True
readLoop.start()
