# !/usr/bin/env python
# -*- coding: utf-8 -*-

# standard library imports
import json  # for working with data file
from threading import Thread
from time import sleep

# local module imports
from blinker import signal
import time
import board
import busio
import gv  # Get access to SIP's settings
import os

try:
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except ImportError:
    print("Trying to install missing Python module adafruit-circuitpython-ads1x15")
    os.system("python3 -m pip install adafruit-circuitpython-ads1x15")
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

SENSOR_DATA_PATH = "./static/data/moisture_sensor_data"
SENSOR_NAME = "sda1115_smt_50"
MAX_VOLTAGE = 3

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

def read_channel():
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create the ADC object using the I2C bus
    ads = ADS.ADS1115(i2c)

    # Create single-ended input on channel 0
    chan = AnalogIn(ads, ADS.P0)
    return chan.voltage

def read_loop():
    while True:
        ts_secs = int(gv.now)
        currentVoltage = read_channel()
        percent = currentVoltage / MAX_VOLTAGE * 100 / 2
        percent = round(percent)
        msd_signal.send(
            "reading", data={"sensor": SENSOR_NAME, "timestamp": ts_secs, "value": percent}
        )
        sensor_file = f"{SENSOR_DATA_PATH}/{SENSOR_NAME}"
        with open(sensor_file, "a") as f:
            f.write(f"{ts_secs * 1000},{percent}\n")
        time.sleep(60 * 5)

moisture_sensor_data_init()

# Run data_test() in baskground thread
readLoop = Thread(target = read_loop)
readLoop.daemon = True
readLoop.start()
