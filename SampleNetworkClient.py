import matplotlib.pyplot as plt
import matplotlib.animation as animation
import time
import math
import socket
import random
import apis
import hashlib
import ssl


class SimpleNetworkClient :
    def __init__(self, port1, port2) :
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
        
        self.infToken = None
        self.incToken = None

        self.ani = animation.FuncAnimation(self.fig, self.updateInfTemp, interval=500)
        self.ani2 = animation.FuncAnimation(self.fig, self.updateIncTemp, interval=500)
        
        #Socket for Infant
        self.infSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.infSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.infSocket.connect(("127.0.0.1",port1))
        self.infSocket = ssl.wrap_socket(self.infSocket, keyfile="key.pem", certfile="cert.pem")
        
        #Socket for Incubator
        self.incSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.incSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
        self.incSocket.connect(("127.0.0.1",port2))
        self.incSocket = ssl.wrap_socket(self.incSocket, keyfile="key.pem", certfile="cert.pem")


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
    
    def getTemperatureFromPort(self, conn, tok) :
        conn.send(b"%s;GET_TEMP" % tok)
        msg = conn.recv(1024)
        m = msg.decode("utf-8")
        return (float(m))
    
    def authenticate(self, conn, pw) :
        conn.send(b"AUTH %s" % pw)
        msg = conn.recv(1024)
        return msg.strip()
    
    def updateInfTemp(self, frame) :
        self.updateTime()
        if self.infToken is None : #not yet authenticated
            self.infToken = self.authenticate(self.infSocket, self.authClient(apis.API_KEY,))

        self.infTemps.append(self.getTemperatureFromPort(self.infSocket, self.infToken)-273)
        #self.infTemps.append(self.infTemps[-1] + 1)
        self.infTemps = self.infTemps[-30:]
        self.infLn.set_data(range(30), self.infTemps)
        return self.infLn,
    
    def updateIncTemp(self, frame) :
        self.updateTime()
        if self.incToken is None : #not yet authenticated
            self.incToken = self.authenticate(self.incSocket, self.authClient(apis.API_KEY,))

        self.incTemps.append(self.getTemperatureFromPort(self.incSocket, self.incToken)-273)
        #self.incTemps.append(self.incTemps[-1] + 1)
        self.incTemps = self.incTemps[-30:]
        self.incLn.set_data(range(30), self.incTemps)
        return self.incLn,

snc = SimpleNetworkClient(23456, 23457)

plt.grid()
plt.show()
