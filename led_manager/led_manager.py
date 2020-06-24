#!/usr/bin/python3

#sudo pm2 start led_manager.py --name led_manager --interpreter python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import json
import random
import subprocess
import re
import threading

mqttClient = None
canPublish = False
connected_to_wifi = False
charging_battery = False
charging_event = threading.Event()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global canPublish
    print("Connected with result code "+str(rc))
    canPublish = True
    client.subscribe("pibot/power/state")
    client.subscribe("pibot/wifi/state")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global charging_event
    global charging_battery
    global connected_to_wifi
    #print(msg.topic+" "+str(msg.payload))
    try:
        if msg.topic == "pibot/wifi/state":
            json_data = json.loads(msg.payload)
            connected_to_wifi = bool(json_data["connected"])
        if msg.topic == "pibot/power/state":
            json_data = json.loads(msg.payload)
            charging_battery = bool(json_data["charging"])
            charging_event.set()
        
    except Exception as e:
        print(f"error : {e}")

def wifi_led():
    global connected_to_wifi
    global mqttClient
    global canPublish
    while True:
        try:
            if canPublish:
                if connected_to_wifi:
                    mqttClient.publish("pibot/leds/cmd", json.dumps({"2" : "0000FF"}))
                else:
                    mqttClient.publish("pibot/leds/cmd", json.dumps({"2" : "000000"}))
                time.sleep(1)

                mqttClient.publish("pibot/leds/cmd", json.dumps({"2" : "0000FF"}))
                time.sleep(1)

        except Exception as e:
            print(f"error : {e}")

def charging_led():
    global charging_battery
    global charging_event
    global mqttClient
    global canPublish
    while True:
        try:
            print(f"charg : {charging_battery}")
            if canPublish:
                if charging_battery:
                    mqttClient.publish("pibot/leds/cmd", json.dumps({"3" : "FF0000"}))
                else:
                    mqttClient.publish("pibot/leds/cmd", json.dumps({"3" : "000000"}))
            
            charging_event.wait(2)
            charging_event.clear()
        except Exception as e:
            print(f"error : {e}")

def main():
    global mqttClient
    global canPublish
    global connected_to_wifi
    
    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    mqttClient.loop_start()

    threading.Thread(name='wifi_led', target=wifi_led).start()
    threading.Thread(name='charging_led', target=charging_led).start()

    while True:
        time.sleep(1)

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