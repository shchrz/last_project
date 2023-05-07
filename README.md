# EasyLence


## Basic Design
![image](https://user-images.githubusercontent.com/109152620/236695505-12707c1a-d5b0-420b-bc4e-01c91fc5bbb8.png)

### Server
The server will be a service that runs on a computer with a connected webcam.
It will get the video from the camera, compress it and send it according to the protocol.
It will also have a broadcast listener waiting for a client to try and find its IP.

### Camera
A standard camera or webcam is connected to the server's computer.

### Protocol
The protocol will be UDP based. It will have a safe mechanism to find if a packet has gone missing or got corrupted. It will be fast and reliable.

### Client
The client will run as a program with GUI and select the server after searching for one with a broadcast packet. After that, the client will set up the Virtual Camera, and then the client will receive data, decompress it, turn it into frames, and then turn the frames into a stream and direct it to the Virtual Camera.

### UI
An interactive User interface to start and use the client, the interface will have a button to set up the Virtual Camera after choosing the server, a way of selecting a server, and a quit button.

### Virtual Camera
On the Client's computer, a driver that will act like an actual camera is connected but will send video directed to it.
    
![image](https://user-images.githubusercontent.com/109152620/236700142-79148267-5968-4409-94ec-44af06831542.png)
