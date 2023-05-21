#GCS end of the communication link
import socket, threading, pickle, cv2, time
import network_performance_metrics as npm

#intializing socket
server_ip = socket.gethostbyname(socket.gethostname()) 
PORT = 5060
ADDR = (server_ip, PORT)
buff_size = 65536 #maximum UDP datagram size
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #server's main socket
server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,buff_size)
server_socket.bind(ADDR)  

#thread subclass, objects will be a thread for each client
class client_thread(threading.Thread): #Pass in the thread class to our subclass definition
    def __init__(self,address): 
        threading.Thread.__init__(self) #initializing thread
        self.event = threading.Event()  #an event flag indicating receiving datagram from client
        self.client_address = address
        self.time_recv = None
        self.data = None #incoming frame
        self.metrics_obj = npm.metrics(self.client_address)
        self.synched = False #indicates if the client and server have finshed synchronising their clocks

    def run(self): #overrides the run function of the inherited thread native class
        while True:
            self.event.wait() #blocks untill it receives a datagram
            while self.event.is_set():
                if not self.synched: #synchronizing client and server's clocks using (PTP Handshake)
                    
                    if self.metrics_obj.sync(self.data,self.time_recv): #returns True if synchronization ended
                        self.synched = True

                else:
                    #video transmission handling
                    deser_datagram = pickle.loads(self.data) #deserialized datagram
                    #unpacking datagram
                    datagram_size = len(self.data)
                    datagram_index = deser_datagram[0]
                    send_time = deser_datagram[1]
                    frame = cv2.imdecode(deser_datagram[2], cv2.IMREAD_COLOR)
                    cv2.imshow(f"FROM {self.client_address}",frame)
                    #calculating & monitoring performance metrics for each client
                    self.metrics_obj.calc_metrics(datagram_index, send_time, datagram_size)

                self.event.clear()
            #window and thread terminating sequence
            key = cv2.waitKey(1) & 0xFF #anding is to avoid Numlk related issue
            if key  == ord('q'):
                break

#handles incoming datagrams and multiplexes them to corresponding thread/client
def start():
    print(f"[LISTENING] Server is listening on {server_ip}")
    client_threads = [] 
    while True:
        msg, address = server_socket.recvfrom(buff_size)
        time_recieved = time.time_ns() #time the datagram was revieved
        #searching if the recieved datagram was from an existing client
        client_index = None
        for _ in range(len(client_threads)):
            if address == client_threads[_].client_address:
                client_index = _
                break 
        
        if client_index == None: #incoming datagram from a new client
            t = client_thread(address)
            client_threads.append(t)
            t.time_recv = time_recieved
            t.data = msg
            t.event.set()
            t.start()
            print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        else: #incoming datagram from an existing client
            client_threads[client_index].data = msg 
            client_threads[client_index].time_recv = time_recieved
            client_threads[client_index].event.set() 
                
        #if all clients have been dropped, the main socket is closed and the connection is terminated
        if threading.active_count()-1 == 0:
            print("CLOSING MAIN SOCKET...")
            server_socket.close()
            cv2.destroyAllWindows()
            break
            

print("[STARTING] server is starting...")
start()