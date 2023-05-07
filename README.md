# EasyLence

Overall, this project will allow a user to use a webcam remotely. For example, imagine you have a camera connected to a computer with the server service running on it, and you want to use it with Zoom on a different computer, so you fire up the client, connect to your server, start the Virtual camera and use it as a regular camera in your Zoom application.
## Basic Design
![image](https://user-images.githubusercontent.com/109152620/236695505-12707c1a-d5b0-420b-bc4e-01c91fc5bbb8.png)

### Server
The server-side service will compress the video data for efficient transmission over the network. Compression reduces the size of the video data, making it faster to transmit and reducing the network bandwidth requirements.

The server-side application will have a listener waiting for the client. When the client-side application sends a broadcast packet, the server-side application will receive it and establish a connection with the client.

The server-side service will monitor broadcast packets from the client. When it finds one, it shall receive it and establish a connection with the client.


### Camera
A standard camera or webcam is connected to the server's computer.

### Protocol
The protocol will be UDP based. It will have a safe mechanism to find if a packet has gone missing or got corrupted. It will be fast and reliable.

### Client
The client application will have a user interface that allows users to find and connect to a server-side service. The client program will send a broadcast packet, which the server-side service will catch and respond to enable the client to establish a connection.

After establishing a connection, the client application will set up a Virtual Camera on the same computer.

Once the Virtual Camera is ready, the client will receive compressed frames. It will decompress them and add them to the Virtual Camera's stream.


### UI
An interactive User interface to start and use the client, the interface will have a button to set up the Virtual Camera after choosing the server, a way of selecting a server, and a quit button.

### Virtual Camera
On the client side, a virtual camera is essentially a software driver that emulates the behavior of a physical camera. It creates a camera-like device on the client's computer that other applications, such as video conferencing software or streaming platforms, such as OBS and Zoom, can be used as a real camera.
    
## Flow
![image](https://user-images.githubusercontent.com/109152620/236700142-79148267-5968-4409-94ec-44af06831542.png)
## Requirements
* Python <= 3.8.11
    * All libraries in requirements.txt
* Windows Computer with a camera and the server software
* Windows Computer with the client software
