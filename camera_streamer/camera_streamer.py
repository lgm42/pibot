#!/usr/bin/python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import picamera
import io
import base64

#sudo pm2 start camera_streamer.py --name camera_streamer --interpreter python3

mqttClient = None

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    
# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        pass
    except Exception as e:
        print(f"error : {e}")

def main():
    global mqttClient

    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    mqttClient.loop_start()

    camera = picamera.PiCamera()
    camera.vflip = True
    camera.hflip = True
    camera.resolution = (1280, 720)
    # Start a preview and let the camera warm up for 2 seconds
    camera.start_preview()
    time.sleep(2)

    stream = io.BytesIO()

    for foo in camera.capture_continuous(stream, 'jpeg',  use_video_port = True):
        try:
            stream.seek(0)
            mqttClient.publish("pibot/camera/stream", base64.b64encode(stream.read()))
            stream.seek(0)
            stream.truncate()
            time.sleep(.1)
        except Exception as e:
            print(f"error : {e}")

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
