#!/usr/bin/python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import json
import random
from rpi_ws281x import *

#sudo pm2 start ws2812.py --name ws2812 --interpreter python3

mqttClient = None
strip = None
led_status = ["000000", "000000", "000000", "000000"]

# LED strip configuration:
LED_COUNT      = 4      # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (18 uses PWM!).
#LED_PIN        = 10      # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL    = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53
 
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("pibot/leds/cmd/#")
    

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        global led_status

        json_data = json.loads(msg.payload)

        if "0" in json_data:
            led_status[0] = json_data["0"]
        if "1" in json_data:
            led_status[1] = json_data["1"]
        if "2" in json_data:
            led_status[2] = json_data["2"]
        if "3" in json_data:
            led_status[3] = json_data["3"]
        update_leds()
    except Exception as e:
        print(f"error : {e}")

def update_leds():
    global led_status
    global strip
    global mqttClient
    try:
        print("driving leds")
        print (led_status)
        for key, value in enumerate(led_status):
            strip.setPixelColor(key, int(value, 16))
        strip.show()
        mqttClient.publish("pibot/leds/state", json.dumps(led_status))
    except Exception as e:
        print(f"error : {e}")

def main():
    global strip
    global led_status
    global mqttClient

    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    #mqttClient.subscribe("$SYS/#")
    mqttClient.loop_start()

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL, WS2812_STRIP)
    # Intialize the library (must be called once before other functions).
    strip.begin()
    update_leds()
    while True:
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
