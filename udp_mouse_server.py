      #     ---------------------------------------------------
      #                    UDP Mouse Server
      #     ---------------------------------------------------
      #         Copyright (C) <2019-2023>
      #        Author : Andreou Pantelis
      #
      # This program is free software: you can redistribute it and/or modify
      # it under the terms of the GNU General Public License as published by
      # the Free Software Foundation, either version 3 of the License, or
      # any later version.
      #
      # This program is distributed in the hope that it will be useful,
      # but WITHOUT ANY WARRANTY;
      #
      # You should have received a copy of the GNU General Public License
      # along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socket
import threading
import socketserver
import time
import math
import ctypes


# win32 mouse events Constants
class Mouse_Events:
    MOUSEEVENTF_ABSOLUTE = 0x8000
    MOUSEEVENTF_MOVE = 0x0001

    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040

    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010

    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_HWHEEL = 0x01000


# wrap via ctypes win32 api mouse_event function
def Do_mouse_event(dwFlags, dx, dy, dwData, dwExtraInfo):
    ret=ctypes.windll.user32.mouse_event(dwFlags, ctypes.c_long(dx), ctypes.c_long(dy), dwData, dwExtraInfo)
    return ret

# wrap win32 api SetCursorPos function
def SetCursorPos(X, Y):
    ctypes.windll.user32.SetCursorPos(int(X), int(Y))


# get ScreenWidth function
def ScreenWidth():
    return ctypes.windll.user32.GetSystemMetrics(0)


# get ScreenHeight function
def ScreenHeight():
    return ctypes.windll.user32.GetSystemMetrics(1)



class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

# wrap win32 api GetCursorPos function
def GetCursorPos():
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return {"x": pt.x, "y": pt.y}




SrceenWH = [ScreenWidth(), ScreenHeight()]

# Server will be started
StopServerFlag = False
Log_Screen=False
ReplyToClient=False



# a usefull class to analyze communication commands
class myProtocol:
    # Protocol Commands Integer Codes
    UNKNOWN_COMMAND = -1
    GET_MOUSE_POS = 0
    SET_MOUSE_POS = 1
    MOUSE_MOVE = 2
    MOUSE_CLICK = 3
    MOUSE_DBCLICK = 4
    MOUSE_DOWN = 5
    MOUSE_UP = 6
    MOUSE_SCROLL = 7
    DISCOVER_IP = 8
    AUTHENTICATION = 9
    START = 10
    STOP = 11
    SCREEN_INFO = 12

    # a command is a triple ->[ StrCommand , IntCommand, ParamsCount  ]
    Commands = [["#GET_MOUSE_POS", GET_MOUSE_POS, 0], ["#SET_MOUSE_POS", SET_MOUSE_POS, 2],
                ["#MOUSE_MOVE", MOUSE_MOVE, 2],
                ["#MOUSE_CLICK", MOUSE_CLICK, 1], ["#MOUSE_DBCLICK", MOUSE_DBCLICK, 1],
                ["#MOUSE_DOWN", MOUSE_DOWN, 1], ["#MOUSE_UP", MOUSE_UP, 1], ["#MOUSE_SCROLL", MOUSE_SCROLL, 1],
                ["#DISCOVER_IP", DISCOVER_IP, 1], ["#AUTHENTICATION", AUTHENTICATION, 2], ["#START", START, 0],
                ["#STOP", STOP, 0],
                ["#SCREEN_INFO", SCREEN_INFO, 0]
                ]

    def GetCommand(StrRequest):
        for c in myProtocol.Commands:
            if str(StrRequest).startswith(c[0]):
                return c[1]
        return myProtocol.UNKNOWN_COMMAND

    def ParseRequest(StrRequest):
        command = myProtocol.GetCommand(StrRequest)
        ret = [command]
        if command != myProtocol.UNKNOWN_COMMAND:
            if myProtocol.Commands[command][2] > 0:
                Params = StrRequest[len(myProtocol.Commands[command][0]):len(StrRequest)]
                Params = Params.strip()
                ret = ret + Params.split()  # splits at any number of spaces
        return ret


prevCommand = myProtocol.UNKNOWN_COMMAND
MouseStartPos = GetCursorPos()

#A threaded udp server
class ThreadedUDPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        server_socket = self.request[1]
        client_host = self.client_address[0]
        client_port = self.client_address[1]

        StrData = data.decode()  # Bytes --> String
        if Log_Screen :
            print("{} wrote:{}".format(self.client_address[0], StrData))

        cmd = StrData.upper()
        cmd_id = myProtocol.GetCommand(cmd)

        params = cmd.split()
        cmd = params[0]
        params = params[1:]
        # print(cmd)
        ProtocolAction(server_socket, self.client_address, cmd, params,cmd_id)
        prevCommand = cmd

        # socket.sendto(data.upper(), self.client_address)


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    pass


def ProtocolAction(server_socket, client_address, cmdRequest, cmdParams, cmdRequest_id):

    global ReplyToClient

    try:
        if cmdRequest_id ==myProtocol.GET_MOUSE_POS : #GET_MOUSE_POS":
            # TODO Action
            current = GetCursorPos()

            ByteMsg = str.encode(cmdRequest + ' ' + str(current["x"]) + " " + str(current['y']))
            server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  == myProtocol.SET_MOUSE_POS : # cmdRequest == "#SET_MOUSE_POS":
            # TODO Action
            newx = float(cmdParams[0])
            newy = float(cmdParams[1])
            # factorx = float(cmdRequest[3])
            # factory = float(cmdRequest[4])

            SetCursorPos(((int(newx * ScreenWidth()), int(newy * ScreenHeight()))))

            if ReplyToClient :
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  ==myProtocol.MOUSE_MOVE : #cmdRequest == "#MOUSE_MOVE" :
            factor1 = 1.2  # 0xffff/SrceenWH[0]
            factor2 = 1.2  # 0xffff/SrceenWH[1]
            dx = round(float(cmdParams[0]) * factor1)
            dy = round(float(cmdParams[1]) * factor2)

            # MouseStartPos=GetCursorPos()
            # newx = int(MouseStartPos["x"] + dx)
            # newy = int(MouseStartPos["y"] + dy)
            # newx = int(1.0*newx/ScreenWidth() * 65535)
            # newy = int(1.0*newy/ScreenHeight() * 65535)
            # Do_mouse_event(Mouse_Events.MOUSEEVENTF_MOVE | Mouse_Events.MOUSEEVENTF_ABSOLUTE, newx, newy, 0, 0)

            Do_mouse_event(Mouse_Events.MOUSEEVENTF_MOVE , dx, dy, 0, 0)

            if ReplyToClient :
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  ==myProtocol.MOUSE_CLICK :  #cmdRequest == "#MOUSE_CLICK":
            # TODO Action
            if cmdParams[0] == "LEFT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif cmdParams[0] == "RIGHT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            elif cmdParams[0] == "MIDDLE":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)

            time.sleep(0.015)

            if cmdParams[0] == "LEFT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif cmdParams[0] == "RIGHT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif cmdParams[0] == "MIDDLE":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)

            if ReplyToClient:
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  == myProtocol.MOUSE_DBCLICK : #cmdRequest == "#MOUSE_DBCLICK":
            if ReplyToClient :
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  ==myProtocol.MOUSE_DOWN: #cmdRequest == "#MOUSE_DOWN":
            if cmdParams[0] == "LEFT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            elif cmdParams[0] == "RIGHT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            elif cmdParams[0] == "MIDDLE":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)

            if ReplyToClient:
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id == myProtocol.MOUSE_UP:  #cmdRequest == "#MOUSE_UP":
            if cmdParams[0] == "LEFT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif cmdParams[0] == "RIGHT":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif cmdParams[0] == "MIDDLE":
                Do_mouse_event(Mouse_Events.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)

            if ReplyToClient:
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id  == myProtocol.MOUSE_SCROLL : #cmdRequest == "#MOUSE_SCROLL":
            delta = int(cmdParams[0])
            Do_mouse_event(Mouse_Events.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)

            if ReplyToClient:
                ByteMsg = str.encode(cmdRequest + " OK!")
                server_socket.sendto(ByteMsg, client_address)


        elif cmdRequest_id == myProtocol.START : #cmdRequest == "#START":
            ByteMsg = str.encode(cmdRequest + " OK!")
            server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id == myProtocol.STOP: #cmdRequest == "#STOP":
            global StopServerFlag
            StopServerFlag = True

            ByteMsg = str.encode(cmdRequest + " OK!")
            server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id == myProtocol.DISCOVER_IP : #cmdRequest == "#DISCOVER_IP":
            ip, port = client_address
            newport = cmdParams[0]
            if newport != "SAME_PORT":
                port = int(cmdParams[0])

            ByteMsg = str.encode(cmdRequest + "_OK!")
            # s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            newAddres = (ip, port)
            if cmdRequest[1] != "SAME_PORT":
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ByteMsg = str.encode(cmdRequest + "_OK!")
                s.sendto(ByteMsg, newAddres)

            else:
                server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id == myProtocol.SCREEN_INFO: #cmdRequest == "#SCREEN_INFO":
            ip, port = client_address

            ByteMsg = str.encode(cmdRequest + "_OK! " + str(ScreenWidth()) + " " + str(ScreenHeight()))
            server_socket.sendto(ByteMsg, client_address)

        elif cmdRequest_id == myProtocol.AUTHENTICATION:  #cmdRequest == "#AUTHENTICATION":
            pass
            # user = cmdParams[0]
            # paswd = cmdParams[1]
            #
            # found = False
            # verified = False
            # for u in Net_Users:
            #     if u[0] == user:
            #         found = True
            #         if u[1] == paswd:
            #             verified = True
            #             auth_token = createAuthToken(client_address)
            #             if auth_token != "NO_TOKEN":
            #                 verified = True
            #                 if len(AuthenticationTokens) < 100:
            #                     AuthenticationTokens.append(auth_token)
            #                 server_socket.sendto(str.encode("AUTHENTICATION_TOKEN_IS " + auth_token), client_address)
            #             else:
            #                 server_socket.sendto(str.encode("AUTHENTICATION_TOKEN_ERROR"), client_address)
            #         break
            #
            # if (not found) or (not verified):
            #     server_socket.sendto(str.encode("INVALID_USERNAME_OR_PASSWORD"), client_address)

        else:
            server_socket.sendto(str.encode("UNKNOWN_COMMAND"), client_address)
    except Exception as e:
        # errno, strerror = e.args
        # print("I/O error({0}): {1}".format(errno, strerror))
        print(e)

        server_socket.sendto(str.encode("BAD_COMMAND"), client_address)
    finally:
        pass


ListenIP = ""
ListenPort = 10010

if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = ListenIP, ListenPort

    server = ThreadedUDPServer((HOST, PORT), ThreadedUDPRequestHandler)
    try:
        ip, port = "127.0.0.1", ListenPort
        print("Server Address = ", ip, ":", port)

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()

        print("Server loop running in thread:", server_thread.name)

        count = 0
        i = 0
        while not StopServerFlag and (count < 8000):
            i = i + 1
            if i % 300000 == 0:
                count = count + 1
                if count % 1000 == 0:
                    print('|Listening..{} |'.format(count))

        server.shutdown()

    finally:
        pass
