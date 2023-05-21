#Drone end of the communication link
import socket, cv2, pickle, imutils, time

buff_size = 65536 #maximum UDP datagram size
#if running on seperate machines substitute with local ip address of server
client_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #sock_stream >> UDP
client_socket.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,buff_size)
client_socket.settimeout(1) #modify
server_ip = socket.gethostbyname(socket.gethostname())
PORT = 5060
 
#synchronizing client and server's clocks using (PTP Handshake)
while True:
    #sending synch message
    print("Sending Synch Message")
    synch_msg = []
    synch_msg.append(time.time_ns()) #synch message timing
    synch_msg.append("0x1")
    client_socket.sendto(pickle.dumps(synch_msg),(server_ip,PORT))
    #recieving delay request
    try:
        print("Recieving Delay Request")
        msg, address = client_socket.recvfrom(buff_size) 
        break
    except socket.timeout as e:
        print("Delay Request Timeout, Restarting Handshake.")

#sending delay response 
print("Delay Request Recieved, Sending Delay Response")
delay_response = []
delay_response.append(time.time_ns()) #delay response timing
delay_response.append("0x3")
while True:
    client_socket.sendto(pickle.dumps(delay_response),(server_ip,PORT))
    try:
        print("Recieving Delay Response Acknowledgment.")
        msg, address = client_socket.recvfrom(buff_size) 
        break
    except socket.timeout as e:
        print("Delay Response Acknowledgment Timeout, Retransmitting Delay Response")

#sending terminating msg 0x5
print("Terminating Handshake sequence, Starting Video Transmission")
client_socket.sendto(pickle.dumps("0x5"),(server_ip,PORT))

#starting video transmission
camera = True
if camera:
	vid = cv2.VideoCapture(0) #0 for webcam , 1 for zed camera (USB input)
else:
	vid = cv2.VideoCapture('videos/1.mp4')

datagram_index = 0

while(vid.isOpened()):
    try:
        #setting up datagram: datagram index + send time + video frame 
        datagram = []
        datagram.append(datagram_index)
        datagram_index += 1

        #setting up video frame
        ret, frame = vid.read() #capturing frame-by-frame
        #frame resizing might be needed
        frame = imutils.resize(frame,width=400)
        ret, encoded_frame = cv2.imencode(".jpg", frame,[int(cv2.IMWRITE_JPEG_QUALITY),40]) #third argument to be tweaked or removed
    
        #appending the remaining sections of the datagram and serializing it before sending
        send_time = time.time_ns()
        datagram.append(send_time)
        datagram.append(encoded_frame) 
        client_socket.sendto(pickle.dumps(datagram),(server_ip,PORT))
        #window terminating sequence
        key = cv2.waitKey(1) & 0xFF #anding is to avoid Numlk related issue
        if key  == ord('q'):
            break
    except socket.error as e:
        print("Datagram Exceeded Maximum Buffer Size Allowed")

#terminating connection and closing windows and camera
client_socket.close()
vid.release()
