#!/usr/bin/python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import json
import random
from ina219 import INA219
from ina219 import DeviceRangeError

#sudo pm2 start ina219_reader.py --name ina219_reader --interpreter python3

SHUNT_OHMS = 0.1
low_pass_filter = 0.8

mqttClient = None

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    #client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def main():
    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    mqttClient.loop_start()

    power = {   
        "voltage" : 0,
        "current" : 0,
        "power" : 0,
        "battery_level" : 0,
        "charging" : True
    }
    print(SHUNT_OHMS)
    ina = INA219(SHUNT_OHMS)
    ina.configure()

    inaV = ina.voltage()
    inaA = ina.current()/1000
    inaW = inaV*inaA

    while True:
        
        inaV = inaV * low_pass_filter + ina.voltage() * (1 - low_pass_filter)
        inaA = inaA * low_pass_filter + ina.current() / 1000 * (1 - low_pass_filter)
        inaW = inaV * inaA

        power["voltage"] = float("{0:.2f}".format(inaV))
        power["current"] = float("{0:.2f}".format(inaA))
        power["power"] = float("{0:.2f}".format(inaW))

        #data interpretation
        if ina.current() < 0.0:
            power['charging'] = True
            power['battery_level'] = None
        else:
            power['charging'] = False
            power['battery_level'] = float("{0:.2f}".format(max(min(170.91 * inaV - 567.75, 100.0), 0.0)))

        mqttClient.publish("pibot/power/state", json.dumps(power))
        time.sleep(1)

def exit_gracefully(signum, frame):
    # restore the original signal handler as otherwise evil things will happen
    # in input when CTRL+C is pressed, and our signal handler is not re-entrant
    signal.signal(signal.SIGINT, original_sigint)

    try:
        if mqttClient is not None:
            mqttClient.disconnect()
        sys.exit(1)

    except KeyboardInterrupt:
        sys.exit(1)

    # restore the exit gracefully handler here    
    signal.signal(signal.SIGINT, exit_gracefully)

if __name__ == '__main__':
    # store the original SIGINT handler
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, exit_gracefully)
    main()