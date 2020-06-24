#!/usr/bin/python3

#sudo pm2 start wifi.py --name wifi --interpreter python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import json
import random
import subprocess
import re

mqttClient = None
canPublish = False

#regex used
#https://regex101.com/r/hU9DVa/2
regex = "^([a-z0-9]*)[ ]*ESSID:\"(.*)\""


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global canPublish
    print("Connected with result code "+str(rc))
    canPublish = True

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def main():
    global mqttClient
    global canPublish
    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    mqttClient.loop_start()

    wifi_status = {   
        "connected" : False,
        "interface" : None,
        "ssid" : None
    }

    while True:
        try:
            ps = subprocess.Popen(['iwgetid'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = subprocess.check_output(('grep', 'ESSID'), stdin=ps.stdout).decode("utf-8") 

            wifi_status["connected"] = True

            result = re.search(regex, output)
            wifi_status["interface"] = result.group(1)
            wifi_status["ssid"] = result.group(2)

        except subprocess.CalledProcessError:
            wifi_status["connected"] = False
            wifi_status["interface"] = None
            wifi_status["ssid"] = None

        if canPublish:
            mqttClient.publish("pibot/wifi/state", json.dumps(wifi_status))

        time.sleep(2)

def exit_gracefully(signum, frame):
    global mqttClient
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