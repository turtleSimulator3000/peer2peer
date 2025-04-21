import socket 
import time
import ipaddress
import threading
import sys
import netifaces
import redis
import platform

os_name = platform.system()
print(f"\nThis is {os_name}")

hostname = socket.gethostname()
print(f"Hostname: {hostname}")

# Multi platform support :)
if os_name == "Windows":
    selfIp = socket.gethostbyname(hostname)

elif os_name == "Linux":
    interface_name = "eth0"
    selfIp = netifaces.ifaddresses(interface_name)[netifaces.AF_INET][0]['addr']

elif os_name == "Darwin":
    interface_name = "en0"
    selfIp = netifaces.ifaddresses(interface_name)[netifaces.AF_INET][0]['addr']



R_Server = redis.StrictRedis(decode_responses=True)
try:
    R_Server.ping()
except:
    print("REDIS: Not Running -- No Streams Available")
    R_Server = None

R_Server.flushall()


lock = threading.Lock()
broadcast = False
endFlag = threading.Event()
threadStorage = []

def murderSock(socket):
    global endFlag
    endFlag.wait()
    socket.close()

def validIP(address):
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False

def Treceiver(connection,address):
   global endFlag
   while not endFlag.is_set(): 
      buf = connection.recv(64)
      #print("Flag:" + str(endFlag.is_set()))
      if len(buf.decode().split()) > 0:
        print('TCP RECVD: ' + str(address[0]) + ' ' + buf.decode().split()[-1]) 

def listenUdp():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serversocket.bind(('', 8082)) 

    socketMurder = threading.Thread(target=murderSock,args=(serversocket,))
    socketMurder.start()

    global endFlag
    while not endFlag.is_set(): 
      try:
        data, address = serversocket.recvfrom(1024)
      except socket.error:
          print("Murdered udp socket")
          break
      print('UDP RECVD: ' + f"{address[0]}" + ' ' + data.decode().split()[-1]) 
      if (f"{address[0]}" != selfIp) and not (str(address[0]) in R_Server.lrange("connections", 0, -1)):
        R_Server.rpush("connections", str(address[0]))
        thread = threading.Thread(target = connectSocket, args = (address[0],))
        thread.start()
    #serversocket.close()


def listenTcp():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.bind(('0.0.0.0', 8082)) 
    serversocket.listen(10)

    socketMurder = threading.Thread(target=murderSock,args=(serversocket,))
    socketMurder.start()

    global endFlag
    try:
        while not endFlag.is_set():
            try:
                connection, address = serversocket.accept() 
            except socket.error:
                print("Murdered tcp socket")
                break
            if (str(address[0]) != selfIp) and not (str(address[0]) in R_Server.lrange("connections", 0, -1)):
                R_Server.rpush("connections", str(address[0]))
                recvThread = threading.Thread(target = Treceiver, args= (connection,address))
                recvThread.start()
    except KeyboardInterrupt:
        print("Stopped Listening tcp")
    
    finally:
        serversocket.close()



def sendBroadcasts():
    global num
    global selfIp
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    #ip_address = client_socket.getsockname()[0]
    global endFlag
    while not endFlag.is_set():
        client_socket.sendto(b'Hello, I am ' + str(selfIp).encode('utf-8') + b' and my number is ' + str(num).encode('utf-8'),("<broadcast>",8082))
        time.sleep(5)
    client_socket.close()


def connectSocket(address):
    lock.acquire_lock()
    global num
    global selfIp
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((address, 8082)) 
    except:
        print("Connection Failed")
        lock.release_lock()
        return False
    lock.release_lock()
    

    global endFlag
    while not endFlag.is_set():
        try:
            client_socket.send(b'Hello, I am ' + str(selfIp).encode('utf-8') + b' and my number is ' + str(num).encode('utf-8'))
            time.sleep(5)
        except socket.error:
            print("Connection terminated")
            break
    
    client_socket.close()

num = -1

if len(sys.argv) > 1:
    numIn = sys.argv[1]
    if len(sys.argv) > 2:
        broadcast = (sys.argv[2] == '-b')
              
else:
    print("Missing arguments")
    print("Usage: python3 app.py NUM [-b]")
    exit()

if(numIn != None and numIn.isnumeric() and int(numIn)>1):
   num = int(numIn)
else:
   print("Invalid Number")
   print("Usage: python3 app.py NUM [-b]")
   exit()

if broadcast:
    thread = threading.Thread(target = sendBroadcasts)
    threadStorage.append(thread)
    thread.start()
    
tcpThread = threading.Thread(target = listenTcp)
threadStorage.append(tcpThread)
tcpThread.start()

udpThread = threading.Thread(target = listenUdp)
threadStorage.append(udpThread)
udpThread.start()



cont = True
while(cont):
   lock.acquire_lock()
   try:
        ipIn = input("Enter a IPv4 address, or type 'exit' to stop: ")
   except KeyboardInterrupt:
       cont = False
       endFlag.set()
      
      
       for thread in threadStorage:
          thread.join()
       sys.exit()
   lock.release_lock()
   print(ipIn)
   if (ipIn == 'exit'):
      cont = False
      endFlag.set()
      
      #raise KeyboardInterrupt
      for thread in threadStorage:
          thread.join()
      sys.exit()
      
   elif(ipIn == 'conns'):
       print(R_Server.lrange("connections", 0, -1))
   else:
        if(validIP(ipIn)):
          thread = threading.Thread(target = connectSocket, args = (ipIn,))
          thread.start()
        else: print("Invalid IP")
         
      


   

