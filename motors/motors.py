#!/usr/bin/python3

import signal
import time
import sys
import paho.mqtt.client as mqtt
import json
import threading
import RPi.GPIO as GPIO

#sudo pm2 start motors.py --name motors --interpreter python3

FORWARD_LEFT=32
BACKWARD_LEFT=29
FORWARD_RIGHT=33
BACKWARD_RIGHT=31
PWM_FREQUENCY=50 #Hz
LOOP_PERIOD = 10 #per sec
mqttClient = None
can_publish = False
motors_status = {"left" : {"speed" : 0, "target" : 0, "slope" : 100}, "right" : {"speed" : 0, "target" : 0, "slope" : 100}}

fl = None
fr = None
bl = None
br = None


 
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global can_publish
    print("Connected with result code "+str(rc))
    can_publish = True
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("pibot/motors/cmd/#")
    

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        global motors_status

        json_data = json.loads(msg.payload)

        if "left" in json_data and "target" in json_data["left"]:
            motors_status["left"]["target"] = json_data["left"]["target"]
        if "right" in json_data and "target" in json_data["right"]:
            motors_status["right"]["target"] = json_data["right"]["target"]
        print (f"motor status updated {motors_status}")   
    except Exception as e:
        print(f"error : {e}")

def check_motor(params, frontGpio, backGpio):
    target = int(params["target"])
    speed = int(params["speed"])
    slope = float(params["slope"])

    if target != speed:
        #we bring the speed to the target value using slope speed
        step = slope / LOOP_PERIOD
        if target > speed:
            #we have to increase speed
            speed = min(target, speed + step)
        else:
            #we have to reduce speed
            speed = max(target, speed - step)

        #drive gpios
        if speed > 0.0:
            frontGpio.ChangeDutyCycle(speed)
            backGpio.ChangeDutyCycle(0.0)
        else:
            frontGpio.ChangeDutyCycle(0.0)
            backGpio.ChangeDutyCycle(-1 * speed)
        params["speed"] = speed

def motor_management():
    global motors_status
    global mqttClient
    global can_publish
    global fl
    global fr
    global bl
    global br

    while True:
        try:
            check_motor(motors_status["left"], fl, bl)
            check_motor(motors_status["right"], fr, br)

            if can_publish:
                mqttClient.publish("pibot/motors/state", json.dumps(motors_status))
            time.sleep(1/LOOP_PERIOD)

        except Exception as e:
            print(f"error : {e}")

def main():
    global mqttClient
    global fl
    global fr
    global bl
    global br
    #application initialization
    mqttClient = mqtt.Client()
    mqttClient.on_connect = on_connect
    mqttClient.on_message = on_message
    #mqttClient.username_pw_set("login", "password")
    mqttClient.connect("127.0.0.1", 1883, 60)
    #mqttClient.subscribe("$SYS/#")
    mqttClient.loop_start()

    #gpio configuration
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(FORWARD_LEFT, GPIO.OUT)
    GPIO.setup(BACKWARD_LEFT, GPIO.OUT)
    GPIO.setup(FORWARD_RIGHT, GPIO.OUT)
    GPIO.setup(BACKWARD_RIGHT, GPIO.OUT)

    fl = GPIO.PWM(FORWARD_LEFT, PWM_FREQUENCY)
    fr = GPIO.PWM(FORWARD_RIGHT, PWM_FREQUENCY)
    bl = GPIO.PWM(BACKWARD_LEFT, PWM_FREQUENCY)
    br = GPIO.PWM(BACKWARD_RIGHT, PWM_FREQUENCY)
    fl.start(0)
    fr.start(0)
    bl.start(0)
    br.start(0)

    threading.Thread(name='motor_management', target=motor_management).start()

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
