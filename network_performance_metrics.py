#monitors latency, jitter, packet loss on a socket
import time, socket, pickle

#intializing socket
server_ip = socket.gethostbyname(socket.gethostname()) 
buff_size = 65536 #maximum UDP datagram size
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #server's main socket
server_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,buff_size) 

class metrics():
    def __init__(self,address):
        self.clientAddress = address
        #synch related attributes
        self.handshake_timings = []
        self.offset = None
        #Latency & Jitter related attributes
        self.latency = 0
        self.jitter = None
        #Packet Loss related attributed
        self.packet_indices = [0]
        self.window_size = 10
        self.error_count = 0
        self.packet_loss = None
        '''
        Network Performance Metrics Log
        Every row is an entry in the log (one run of the calc_metrics function)
        column 0: datagram index, column 1: latency. column 2: jitter,
        column 3: packet loss, column 4: datagram size
        '''
        self.log = []
    
    def sync(self, ser_handshake_msg, time_recieved):
        #deserializing handshake message
        handshake_msg = pickle.loads(ser_handshake_msg)
        #handshake stages: synch msg 0x1, delay request 0x2, delay response 0x3, terminating handshake 0x4
        if handshake_msg[1] == "0x1": #First stage
            #recieving synch msg
            print("Synch Message Recieved")
            self.handshake_timings.append(handshake_msg[0]) #synch message timing
            time_to_get_here = time.time_ns() - time_recieved
            self.handshake_timings.append(time.time_ns() - time_to_get_here) #recieved synch message timing
            #sending delay request
            print("Sending Delay Request")
            delay_request = []
            self.handshake_timings.append(time.time_ns()) #delay request timing
            delay_request.append(self.handshake_timings[2])
            delay_request.append("0x2")
            server_socket.sendto(pickle.dumps(delay_request),self.clientAddress)
            return False 

        elif handshake_msg[1] == "0x3": #Third stage
            #recieving delay response
            print("Delay Response Recieved")
            self.handshake_timings.append(handshake_msg[0]) #delay response timing
            #calculating the offset between the two clocks to synchronise them
            self.offset = round((((self.handshake_timings[1] - self.handshake_timings[0]) + 
            (self.handshake_timings[2] - self.handshake_timings[2])) / 2) * 1e-9,6)
            server_socket.sendto(pickle.dumps("0x4"),self.clientAddress) #terminating handshake
            return False

        else: #indicates handshake termination, wether a terminating message was recieved or a frame
            print("Terminating Handshake sequence, Starting Video Transmission")
            return True
    
    def calc_metrics(self, datagram_index, send_time, datagram_size):
        #Calculating Latency and jitter
        recv_time = time.time_ns()
        temp = round((recv_time - send_time) * 1e-6 - self.offset, 6) #temp latency var to calculate jitter
        self.jitter = abs(temp - self.latency)
        self.latency = temp 
        #Calculating Packet Loss
        #packet loss will be calculated for a moving window
        self.packet_indices.append(datagram_index)
        #checking for dropped packets
        if (self.packet_indices[len(self.packet_indices)-1] - self.packet_indices[len(self.packet_indices)-2]) != 1:
            self.error_count += 1
        
        #when the window size is accumlated, packet loss is calculated for said window 
        if (len(self.packet_indices) + self.error_count) == self.window_size:
            self.packet_loss = (self.error_count / self.window_size) * 100
            self.error_count = 0
            temp = self.packet_indices[len(self.packet_indices)-1]
            self.packet_indices.clear()
            self.packet_indices.append(temp)

        print(f"[Packet: {datagram_index}  |  Latency: {self.latency} ms | Jitter: {self.jitter} "
        f"| Packet Loss: {self.packet_loss}% |  Datagram size: {datagram_size}  ]")

        #Logging this run of the function for final evaluation and writing session details to a csv file
        self.log.append([datagram_index,self.latency,self.jitter,self.packet_loss,datagram_size])

    def final_evaluation():
        pass

    def write_to_csv():
        pass