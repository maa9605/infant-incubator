import threading
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import infinc
import time
import math
import socket
import fcntl
import os
import errno
import random
import string
import hashlib
import apis
import ssl

class SmartNetworkThermometer (threading.Thread) :
    open_cmds = ["AUTH", "LOGOUT"]
    prot_cmds = ["SET_DEGF", "SET_DEGC", "SET_DEGK", "GET_TEMP", "UPDATE_TEMP"]

    def __init__ (self, source, updatePeriod, port) :
        threading.Thread.__init__(self, daemon = True) 
        #set daemon to be true, so it doesn't block program from exiting
        self.source = source
        self.updatePeriod = updatePeriod
        self.curTemperature = 0
        self.updateTemperature()
        self.tokens = []
	
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #wrap TCP socket in an SSL wrapper
        self.serverSocket = ssl.wrap_socket(self.serverSocket, server_side=True, keyfile="key.pem", certfile="cert.pem")
        self.serverSocket.bind(("127.0.0.1", port))
        self.serverSocket.listen(0)
        fcntl.fcntl(self.serverSocket, fcntl.F_SETFL, os.O_NONBLOCK)

        self.deg = "K"
    '''    
    def authClient(self, raw): #hashing function for the tokens and API keys
    	hashObj = hashlib.sha256()
    	saltedRaw = "12345" + raw
    	
    	hashObj.update(raw.encode())
    	hashedPass = bytes(hashObj.hexdigest(), 'utf-8')
    	return hashedPass
    '''	
    def authClient(self,raw,nonce=''): #hashing function for the tokens and API keys
   
        hashObj = hashlib.sha256()
        saltedRaw = "12345" + raw
           
        #if there is a nonce string use it to verify the hash that was sent. 
        if nonce == '':
           nonce = str(random.getrandbits(16))
        else: 
           nonce = nonce #raw[1:int(raw[:1])+1]
      
        noncedsaltedRaw = nonce + saltedRaw
        hashObj.update(noncedsaltedRaw.encode())
        hashedPass = bytes(hashObj.hexdigest(), 'utf-8')
        hashedPass = bytes(str(len(nonce)),'utf-8') + bytes(nonce,'utf-8') + hashedPass
        
        return hashedPass
        
    def sendMessage(self, conn, message):  #consolidated all send message functions in one function 
    
        msg = message.encode("utf-8")
        conn.send(msg)
        
    def setSource(self, source) :
        self.source = source

    def setUpdatePeriod(self, updatePeriod) :
        self.updatePeriod = updatePeriod 

    def setDegreeUnit(self, s) :
        self.deg = s
        if self.deg not in ["F", "K", "C"] :
            self.deg = "K"

    def updateTemperature(self) :
        self.curTemperature = self.source.getTemperature()

    def getTemperature(self) :
        if self.deg == "C" :
            return self.curTemperature - 273
        if self.deg == "F" :
            return (self.curTemperature - 273) * 9 / 5 + 32

        return self.curTemperature

    def processCommands(self, msg, conn) :
        cmds = msg.split(';')
        for c in cmds :
            cs = c.split(' ')
            if len(cs) == 2 : #should be either AUTH or LOGOUT
                if cs[0] == "AUTH":
                    #limit the number of connected users with tokens to 10
                    if bytes(cs[1],'utf-8') == self.authClient(apis.API_KEY,cs[1][1:int(cs[1][:1])+1]) and len(self.tokens) < 10: 
                        self.tokens.append(''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(16)))
                        self.sendMessage(conn, self.tokens[-1])
                    else:
                        print("Max Connections Reached!")
                        
                elif cs[0] == "LOGOUT":
                    if cs[1] in self.tokens :
                        self.tokens.remove(cs[1])
                else : #unknown command
                    self.sendMessage(conn, "Invalid Command\n")
              
            elif c == "SET_DEGF" :
                self.deg = "F"
            elif c == "SET_DEGC" :
                self.deg = "C"
            elif c == "SET_DEGK" :
                self.deg = "K"
            elif c == "GET_TEMP" :
                self.sendMessage(conn, "%f\n" % self.getTemperature())
            elif c == "UPDATE_TEMP" :
                self.updateTemperature()
            elif c :
                self.sendMessage(conn, "Invalid Command\n")
               
        

    def run(self) : #the running function
        while True : 
            try :
               connection, addr = self.serverSocket.accept()
               while True:
                  msg = connection.recv(1024)
                  msg = msg.decode("utf-8").strip()
                  cmds = msg.split(' ')
                  
                  if len(cmds) == 1 : # protected commands case
                     semi = msg.find(';')
                     if semi != -1 : #if we found the semicolon
                        #print (msg)
                        if msg[:semi] in self.tokens : #if its a valid token NEED TO ADD SOMETHING HERE TO HASH THE TOKENS FOR TRANSIT 
                           self.processCommands(msg[semi+1:], connection)
                        else :
                            self.sendMessage(conn, "Bad Token\n")
                
                  elif len(cmds) == 2 :
                     if cmds[0] in self.open_cmds : #if its AUTH or LOGOUT
                        self.processCommands(msg, connection) 
                     else :
                        self.sendMessage(conn, "Authenticate First\n")
                  else :
                     # otherwise bad command
                     self.sendMessage(conn, "Bad Command\n")
                
            except IOError as e :
                if e.errno == errno.EWOULDBLOCK :
                    #do nothing
                    pass
                else :
                    #do nothing for now
                    pass
                msg = ""

 

            self.updateTemperature()
        
            time.sleep(self.updatePeriod)


class SimpleClient :
    def __init__(self, therm1, therm2) :
        self.fig, self.ax = plt.subplots()
        now = time.time()
        self.lastTime = now
        self.times = [time.strftime("%H:%M:%S", time.localtime(now-i)) for i in range(30, 0, -1)]
        self.infTemps = [0]*30
        self.incTemps = [0]*30
        self.infLn, = plt.plot(range(30), self.infTemps, label="Infant Temperature")
        self.incLn, = plt.plot(range(30), self.incTemps, label="Incubator Temperature")
        plt.xticks(range(30), self.times, rotation=45)
        plt.ylim((20,50))
        plt.legend(handles=[self.infLn, self.incLn])
        self.infTherm = therm1
        self.incTherm = therm2

        self.ani = animation.FuncAnimation(self.fig, self.updateInfTemp, interval=500)
        self.ani2 = animation.FuncAnimation(self.fig, self.updateIncTemp, interval=500)

    def updateTime(self) :
        now = time.time()
        if math.floor(now) > math.floor(self.lastTime) :
            t = time.strftime("%H:%M:%S", time.localtime(now))
            self.times.append(t)
            #last 30 seconds of of data
            self.times = self.times[-30:]
            self.lastTime = now
            plt.xticks(range(30), self.times,rotation = 45)
            plt.title(time.strftime("%A, %Y-%m-%d", time.localtime(now)))


    def updateInfTemp(self, frame) :
        self.updateTime()
        self.infTemps.append(self.infTherm.getTemperature()-273)
        #self.infTemps.append(self.infTemps[-1] + 1)
        self.infTemps = self.infTemps[-30:]
        self.infLn.set_data(range(30), self.infTemps)
        return self.infLn,

    def updateIncTemp(self, frame) :
        self.updateTime()
        self.incTemps.append(self.incTherm.getTemperature()-273)
        #self.incTemps.append(self.incTemps[-1] + 1)
        self.incTemps = self.incTemps[-30:]
        self.incLn.set_data(range(30), self.incTemps)
        return self.incLn,

UPDATE_PERIOD = .05 #in seconds
SIMULATION_STEP = .1 #in seconds

#create a new instance of IncubatorSimulator
bob = infinc.Human(mass = 8, length = 1.68, temperature = 36 + 273)
#bobThermo = infinc.SmartThermometer(bob, UPDATE_PERIOD)
bobThermo = SmartNetworkThermometer(bob, UPDATE_PERIOD, 23456)
bobThermo.start() #start the thread

inc = infinc.Incubator(width = 1, depth=1, height = 1, temperature = 37 + 273, roomTemperature = 20 + 273)
#incThermo = infinc.SmartNetworkThermometer(inc, UPDATE_PERIOD)
incThermo = SmartNetworkThermometer(inc, UPDATE_PERIOD, 23457)
incThermo.start() #start the thread

incHeater = infinc.SmartHeater(powerOutput = 1500, setTemperature = 45 + 273, thermometer = incThermo, updatePeriod = UPDATE_PERIOD)
inc.setHeater(incHeater)
incHeater.start() #start the thread

sim = infinc.Simulator(infant = bob, incubator = inc, roomTemp = 20 + 273, timeStep = SIMULATION_STEP, sleepTime = SIMULATION_STEP / 10)

sim.start()

sc = SimpleClient(bobThermo, incThermo)

plt.grid()
plt.show()

