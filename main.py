import pyglet
from pyglet.gl import *
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from threading import Thread
import http.server
import socketserver
import socket
import pyqrcode
import os
import random

win = pyglet.window.Window(resizable=True)
display = pyglet.canvas.Display()
screen = display.get_default_screen()

screenSize = [0, 0]
clients = []
paddlePositions = [0, 0]
ballDirection = ""
ballCoords = [int(screenSize[0]/2), int(screenSize[1]/2)]
ballAngle = 0
speed = 1.0

html = """
<html>
  <head>
    <link rel="stylesheet" href="style" />
    <title>pyPong</title>
  </head>
  <body bgcolor="#000000">
    <button id="up">^</button>
    <br />
    <button id="down">v</button>
  </body>
  <script src="script"></script>
</html>"""

script = """
var inputSocket = new WebSocket("ws://{{ host }}:8000");
document.getElementById("up").onclick = function (evt) {
  inputSocket.send("U");
};
document.getElementById("down").onclick = function (evt) {
  inputSocket.send("D");
};
"""

style = """
button {
  background-color: #4CAF50; 
  color: white;
  padding: 100px 50%;
  text-align: center;
  font-size: 300px;
  touch-action: manipulation;
}
"""

class GetInput(WebSocket):
    def handleMessage(self):
        global ballCoords, ballDirection
        if ballDirection == "":
            ballDirection = "R"
            ballCoords = [int(screenSize[0]/2), int(screenSize[1]/2)]
        i = 0
        for client in clients:
            if client == self:
                if self.data == "U":
                    paddlePositions[i] += 30
                elif self.data == "D":
                    paddlePositions[i] -= 30
                break
            i += 1

    def handleConnected(self):
        print(self.address, 'connected')
        clients.append(self)

    def handleClose(self):
        print(self.address, 'closed')
        clients.remove(self)


class getController(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(html, "utf8"))
            return
        if self.path == '/script':
            self.send_response(200)
            self.send_header("Content-type", "text/javascript")
            self.end_headers()
            self.wfile.write(bytes(script.replace("{{ host }}",get_ip()), "utf8"))
            return
        if self.path == '/style':
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            self.wfile.write(bytes(style, "utf8"))
            return
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


def scanBall(a):
    global ballCoords, paddlePositions, ballDirection, ballAngle, speed
    if (10 <= int(ballCoords[0]) <= 40) and (paddlePositions[0] <= int(ballCoords[1]) <= paddlePositions[0]+200*(2-speed)):
        print("hitL")
        ballDirection = "R"
        ballAngle = abs(paddlePositions[0]+100-ballCoords[0]) / random.randint(45000,55000)
        speed += 0.05
        if paddlePositions[0] + 100 > ballCoords[1]:
            ballAngle = -ballAngle
    elif (screenSize[0]-40 <= int(ballCoords[0]) <= screenSize[0] - 10) and (paddlePositions[1] <= int(ballCoords[1]) <= paddlePositions[1]+200*(2-speed)):
        print("hitR")
        ballDirection = "L"
        ballAngle = abs(paddlePositions[1] + 100 - ballCoords[0]) / random.randint(45000,55000)
        speed += 0.05
        if paddlePositions[1] + 100 > ballCoords[1]:
            ballAngle = -ballAngle
    elif (10 <= int(ballCoords[0]) <= 40) and not (paddlePositions[0] <= int(ballCoords[1]) <= paddlePositions[0]+200*(2-speed)):
        print("goalL")
        ballDirection = ""
        ballCoords = [int(screenSize[0] / 2), int(screenSize[1] / 2)]
        ballAngle = 0
        speed = 1.0
    elif (screenSize[0]-40 <= int(ballCoords[0]) <= screenSize[0] - 10) and not (paddlePositions[1] <= int(ballCoords[1]) <= paddlePositions[1]+200*(2-speed)):
        print("goalR")
        ballDirection = ""
        ballCoords = [int(screenSize[0] / 2), int(screenSize[1] / 2)]
        ballAngle = 0
        speed = 1.0
    elif ballCoords[1] > screenSize[1] or ballCoords[1] < 0:
        ballAngle = - ballAngle


def moveBall():
    global ballDirection, ballAngle, ballCoords, speed
    if ballDirection == "L":
        ballCoords[0] -= 10*speed
        ballCoords[1] = ballCoords[1]+ballCoords[0]*ballAngle
    elif ballDirection == "R":
        ballCoords[0] += 10*speed
        ballCoords[1] = ballCoords[1]+ballCoords[0]*ballAngle


def drawBall():
    global ballCoords, ballDirection
    if ballDirection != "":
        pyglet.graphics.draw_indexed(4, pyglet.gl.GL_TRIANGLES,
                                     [0, 1, 2, 0, 2, 3],
                                     ('v2i', (int(ballCoords[0]), int(ballCoords[1]),
                                              int(ballCoords[0]), int(
                                                  ballCoords[1]+20),
                                              int(ballCoords[0]) +
                                              30, int(ballCoords[1]+20),
                                              int(ballCoords[0]+30), int(ballCoords[1]))))


def drawPaddles():
    global paddlePositions
    pyglet.graphics.draw_indexed(4, pyglet.gl.GL_TRIANGLES,
                                 [0, 1, 2, 0, 2, 3],
                                 ('v2i', (10, int(paddlePositions[0]),
                                          10, int(paddlePositions[0]+200*(2-speed)),
                                          40, int(paddlePositions[0]+200*(2-speed)),
                                          40, int(paddlePositions[0])))
                                 )
    pyglet.graphics.draw_indexed(4, pyglet.gl.GL_TRIANGLES,
                                 [0, 1, 2, 0, 2, 3],
                                 ('v2i', (screenSize[0]-10, int(paddlePositions[1]),
                                          screenSize[0] -
                                          10, int(paddlePositions[1]+200*(2-speed)),
                                          screenSize[0] -
                                          40, int(paddlePositions[1]+200*(2-speed)),
                                          screenSize[0]-40, int(paddlePositions[1])))
                                 )


def startSocket():
    server = SimpleWebSocketServer(get_ip(), 8000, GetInput)
    server.serveforever()


def startAPI():
    my_server = socketserver.TCPServer(("", 80), getController)
    my_server.serve_forever()


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


@win.event
def on_draw():
    moveBall()
    glClear(GL_COLOR_BUFFER_BIT)
    drawPaddles()
    drawBall()


@win.event
def on_resize(width, height):
    global screenSize
    screenSize[1] = height
    screenSize[0] = width


@win.event
def on_close():
    win.close()
    os._exit(0)


url = pyqrcode.create("http://"+get_ip())
print(url.terminal(quiet_zone=1))
Thread(target=startSocket).start()
Thread(target=startAPI).start()
pyglet.clock.schedule_interval(scanBall, 1/30)
pyglet.app.run()