import socket
serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('0.0.0.0', 8082)) 
serversocket.listen(5)

def receiver(connection):
   running = True
   while running: 
      buf = connection.recv(64)
      print('Got:', buf) 




connection, address = serversocket.accept() 
receiver(connection)
serversocket.close()


