#@author Kenan El-Gaouny
import serial
from socket import *
import json
import requests
import datetime
from time import sleep
import RPi.GPIO as GPIO

class RPI_Handler:
    def __init__(self): ## initialize instance and set variables
        self.ser=serial.Serial("COM4",9600)
        self.nodeAddrList=["192.168.2.83"] ## input node ips in here
        self.SERVERAPI = "http://172.17.82.126:3001/api"
        self.NODE_ID = 'Test1'
        self.garageStatus=""
        self.socket= socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(1)

    def main(self):
        print "starting up"
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(2, GPIO.OUT)
        previousAlarm = False ## keep track of alarm to reset it
        while True:
            print "getting values from arduino "
            values=self.getSensorData() ## get the sensor data
            print values
            try:
                if "alarm" in values:
                    print "got alarm creating json and sendig"
                    data = self.createAlarmJSON(values) ## alarm  recieved create json for it
                    values = self.getSensorData() ## alarm values in here
                    self.sendAlarm(data)
                    previousAlarm = True
                else:
                    print "got data" ## normal data packet recieved
                    data = self.createJSON(values)
                    print data
                    print "updating garage sttatus from data"
                    self.garageStatusUpdate(data["values"]["garage"])
                    if previousAlarm:
                        print "sending reset alarm to other nodes to disable alarms" ## used to disable alarms on other nodes if trigerred earlier
                        previousAlarm = False
                        self.resetAlarm()
                    print "sending data to server "
                    self.sendJSON(data, "/nodes/values")
            except:
               print("EXCEPTION IN mains while loop, probably server or udp related")
            sleep(0.1)



    def getSensorData(self): ## read values on serial port sent by arduino
        complete = ""
        while (True):
            data = self.ser.read()
            complete = complete + data
            if (data == "\n"):
                return (complete)

    def garageStatusUpdate(self, data): ## to update garage status
        if data != self.garageStatus:
            print "turned off garage gpio pin"
            GPIO.output(2, 0)
            print "gpio 2 low"
        self.garageStatus=data

    def createAlarmJSON(self,data):
        try:
            dict=json.loads(data)
            dict['time'] = self.timestamp()
            dict['id'] = self.NODE_ID
            return  dict
        except:
            print("bad alarm data recived")


    def createJSON(self,data):
        try:
            dict=json.loads(data)
            dict['time'] = self.timestamp()
            dataDict = {}
            dataDict['id'] = self.NODE_ID
            dataDict['values'] = dict
            return  json.loads(json.dumps(dataDict))
        except:
            print("bad data recived")

    def sendJSON(self, data, route):
        try:
            requests.post(self.SERVERAPI + route, json=data)
        except:
            print("couldnt send to server")


    def sendAlarm(self,data):
        print "sending alarm to server"
        self.sendJSON(data, "/nodes/emergency");
        print "sending alarm to nodes via udp"
        for addr in self.nodeAddrList:
            i = 0
            while True:
              print  "waiting for ack"
              try:
                self.socket.sendto("TriggerAlarm", (addr, 2000))
                ## WAIT FOR SEVER ACK HERE if not try again
                message, address = self.socket.recvfrom(1024)
              except:
                  print "COULDNT SEND OR RECIVED UDP"
              if "ACK" in message:
                  break
              if i >= 2: ## try three times before giving up on node
                  print "giving up no reply"
                  break
              i = i+1

    def resetAlarm(self):
        ## do this once the alarm values go away
        print "resetting alarm as requested"
        for addr in self.nodeAddrList:
            i=0
            while True:
              try:
                self.socket.sendto("ResetAlarm", (addr, 2000))
                ## WAIT FOR SEVER ACK HERE if not try again
                message, address = self.socket.recvfrom(1024)
              except:
                  print "COULDNT SEND OR RECIVED UDP"
              if "ACK" in message:
                  break
              if i >= 2: ## try three times before giving up on node
                  print "giving up no reply"
                  break
              i = i+1

    def timestamp(self):
        return datetime.datetime.now().isoformat()

if __name__== "__main__":
    x=RPI_Handler()
    x.main()
