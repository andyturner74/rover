# Attach: SR-04 Range finder, switch on SW1, and of course motors.

# The switch SW2 stops and starts the robot

#from rrb3 import *
import time, random
import VL53L0X
from rrb3 import *
import RPi.GPIO as GPIO
import smbus
import threading

IN1 = 17    # pin11  
IN2 = 18  
IN3 = 27  
IN4 = 22  

bus = smbus.SMBus(1)

address = 0x44
encoder = 0

lastTurnRight = False
tofCounter = 0

tof = VL53L0X.VL53L0X()

tof.start_ranging(VL53L0X.VL53L0X_BETTER_ACCURACY_MODE)

timing = tof.get_timing()
if (timing < 20000):
    timing = 20000 


BATTERY_VOLTS = 9
MOTOR_VOLTS = 6

rr = RRB3(BATTERY_VOLTS, MOTOR_VOLTS)

#rr.set_motors(.005, 0, .005, 0)

# if you dont have a switch, change the value below to True
running = False

usingTof = True

def stepperMotorFindHome():
    while tof.get_distance() > 40:
        backward(0.003, 3)
    stop()
    while tof.get_distance() < 40:
        forward(0.003, 3)
    stop()
# now center the sensor
    forward(0.003, 120)
    stop()



def stepperMotorSweep():
    stepperMotorFindHome()

    while True:
        backward(0.005, 64) #sweep 45 degrees
        stop()
        time.sleep(.01)
        forward(0.005, 64)  #sweep 45 degrees
        stop()
        time.sleep(0.01)
        forward(0.005, 64)  #sweep 45 degrees
        stop()
        time.sleep(0.01)
        backward(0.005, 64) #sweep 45 degrees
        stop()
        time.sleep(4)


def setStep(w1, w2, w3, w4):  
    GPIO.output(IN1, w1)  
    GPIO.output(IN2, w2)  
    GPIO.output(IN3, w3)  
    GPIO.output(IN4, w4)

def stop():  
    setStep(0, 0, 0, 0)

def stop():  
    setStep(0, 0, 0, 0)  

def forward(delay, steps):    
    for i in range(0, steps):  
        setStep(1, 0, 0, 0)  
        time.sleep(delay)  
        setStep(0, 1, 0, 0)  
        time.sleep(delay)  
        setStep(0, 0, 1, 0)  
        time.sleep(delay)  
        setStep(0, 0, 0, 1)  
        time.sleep(delay)  

def backward(delay, steps):    
    for i in range(0, steps):  
        setStep(0, 0, 0, 1)  
        time.sleep(delay)  
        setStep(0, 0, 1, 0)  
        time.sleep(delay)  
        setStep(0, 1, 0, 0)  
        time.sleep(delay)  
        setStep(1, 0, 0, 0)  
        time.sleep(delay)  



def readNumber():
    try:
        number = bus.read_byte(address)
    except Exception as E:
        print "error reading arduino"
        number = -1

    return number


def turn_randomly():
    turn_time = random.randint(1, 3)
    if random.randint(1, 2) == 1:
        rr.left(turn_time, 0.25) # turn at half speed
    else:
        rr.right(turn_time, 0.25)
    rr.stop()


def findClearPath(tof):
    print 'find clear path called'
    rr.stop()
    distanceTof = tof.get_distance()
    counter = 0
    rr.left(5, .15)
    while distanceTof > -2 and distanceTof < 8000:
        counter = counter + 1
        encoder = readNumber()   
        if encoder == 0 and running:
            rr.stop()
            return 0       
        distanceTof = tof.get_distance()
        if counter > 14:
            rr.stop()
            return 0
    return 1



def turnFromObstacle():
    distanceTof = tof.get_distance()
    counter = 0
    while distanceTof > 0 and distanceTof < 250:
        if counter > 5:
            rr.stop()
            goBackwards()
            counter = 0
        rr.right(0.20, 0.25)
        distanceTof = tof.get_distance()
        counter = counter + 1
    if distanceTof == 0:
        rr.stop()
        goBackwards()
        rr.right(0.20, 0.25)        

def clickcallback(channel):
    #interrupt handler callback
    print "Interrupt detected"
    click = sensor.getClick()
    print "Click detected (0x%2X)" % (click)
    if (click & 0x10): print " single click"
    if (click & 0x20): print " double click"

def goBackwards():
    rr.reverse(2, .15)
    time.sleep(0.1)
    encoder = readNumber()
    if encoder == 0 and running:  #we've hit something trying to back up
        #try doing a random turn instead
        turn_randomly()
        goBackwards()
        

def getUnstuck(lastTurnRight):
    rr.stop()
    goBackwards()
    if lastTurnRight:
        rr.left(2, .15)
        lastTurnRight = False
    else:
        rr.right(1.5, .15)
        lastTurnRight = True


index = 0

def setup():  
    GPIO.setwarnings(False)   
    GPIO.setup(IN1, GPIO.OUT)      # Set pin's mode is output  
    GPIO.setup(IN2, GPIO.OUT)  
    GPIO.setup(IN3, GPIO.OUT)  
    GPIO.setup(IN4, GPIO.OUT)  


try:

    setup()

    distanceTof = tof.get_distance()

    stepperThread = threading.Thread(target=stepperMotorSweep)
    stepperThread.start()



    while True:
        encoder = readNumber()

        if encoder == 0 and running:
            getUnstuck(lastTurnRight)
           
        distanceTof = tof.get_distance()
        

        print distanceTof

        if distanceTof > 0 and distanceTof < 30: #way too close to something
            getUnstuck(lastTurnRight)

        if distanceTof > 30 and distanceTof < 200 and running:
            tofCounter = tofCounter + 1
            if tofCounter > 5: #then we're stuck on something
                tofCounter = 0
                getUnstuck(lastTurnRight)
            elif findClearPath(tof) == 0:
                turnFromObstacle()



        if running:
            #rr.set_motors(.255, 0, .255, 0)
            rr.forward(0, .25)
        if rr.sw2_closed():
            running = not running
        if not running:
            rr.stop()
        time.sleep(0.2)
except KeyboardInterrupt:
    def destroy():  
        GPIO.cleanup()             # Release resource          
finally:
    print("Exiting")
    rr.cleanup()
    
