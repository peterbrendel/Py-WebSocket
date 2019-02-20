# Dear me from future, 
#   add an event handler somehow 
# Thanks,
# Me.

import sys
import math
import json
import asyncio
import websockets
from enum import IntEnum
from sortedcontainers import SortedSet as oset
from Client import Client

# Packet Identifier enumerator #
class PacketIdentifier(IntEnum):
    P_CONNECT = 1
    P_REFRESH = 2

# --- #
#
# Constants #
MAX_PLAYERS = 10
HOSTNAME = 'localhost'
PORT = 1501

# End of Constants #
#
# Control variables #
connected = list()
available_index = oset([0,1,2,3,4,5,6,7,8,9])
map_positions = []

# End of Control variables #
#
# Player class definition #
class Player(Client):
    def __init__(self, i, websocket, x, y, a):
        Client.__init__(self,i, websocket)
        self.x = x
        self.y = y
        self.a = a

    def getData(self):
        return "{:.3f},{:.3f},{:.3f}".format(self.x, self.y, self.a)


# End of Player class definition #
#
#
#   # Send the actual message to recipient(s)
def message_loop(message, recipients):
    for recipient in recipients:
        recipient.pre_send(message)

#   # Broadcast some data to all clients based on PacketIdentifier
def broadcast(data, identifier):
    recipients = list(connected)
    message = None
    if identifier == PacketIdentifier.P_REFRESH:    
        message = json.dumps(
            {
                "PacketId": int(identifier),
                "i": data[0],
                "x": data[1],
                "y": data[2]
            }
        )
    
    if message is not None:
        message_loop(message, recipients)

#   # Broadcast connection data to all clients except new one
def broadcast_except(player, identifier):
    recipients = list(filter(lambda p: p is not player, connected))
    identifier = int(identifier)
    message = json.dumps(
        {
            "PacketId": identifier,
            player.i: player.getData()
        }
    )
    if message is not None:
        message_loop(message, recipients)

#   # Initiate new player on server (Give a map position + angle) and broadcast_except
def initiate(player):
    message = dict()
   
    message = dict(map(lambda p: (p.i, p.getData()), connected))
    message["PacketId"] = PacketIdentifier.P_CONNECT
    message["Player"] = message.pop(player.i)
    message["YourId"] = player.i
    player.json_prepare(message)
    broadcast_except(player, PacketIdentifier.P_CONNECT)

#   Handle the message incoming from clients
def message_handle(player, websocket, message):
    if player is not None:
        data = list(map(float,message.split(',')))
        print("Player {} data {}".format(player.i, data))
        data.insert(0, player.i)
        broadcast(data, PacketIdentifier.P_REFRESH)

# Handle new connections / Packets per client                                           -- Believe that global index should eventually break the system 
async def handler(websocket, path):
    global index
    if len(connected) >= MAX_PLAYERS:
        websocket.send("server is full")
        websocket.close()
        return

    index = available_index[0]
    available_index.remove(index)
    player = addPlayer(index, websocket)

    producer_task = asyncio.ensure_future(player.produce())
    listener_task = asyncio.ensure_future(websocket.recv())
    initiate(player)

    try:
        while player.alive:
            done, pending = await asyncio.wait([producer_task, listener_task], return_when=asyncio.FIRST_COMPLETED)
            if producer_task in done:
                messages = producer_task.result()
                if websocket.open:
                    for message in messages:
                        await websocket.send(message)
                    producer_task = asyncio.ensure_future(player.produce())
                else:
                    player.alive = False
                    try:
                        connected.remove(player)
                        available_index.add(player.i)
                        delPlayer(player)
                    except:
                        print("could not remove client {}".format(player.i))
            if listener_task in done:
                message = listener_task.result()
                if message is None:
                    player.alive = False
                    try:
                        connected.pop(player)
                        available_index.add(client.i)
                        delPlayer(player)
                    except:
                        print("could not remove client {}".format(player.i))
                else:
                    message_handle(player, websocket, message)
                    listener_task = asyncio.ensure_future(websocket.recv())
    except:
        print("Disconnecting player {}".format(player.i))
        player.alive = False
        connected.remove(player)
        available_index.add(player.i)
        print(available_index)
        delPlayer(player)

#   # Handle logic of adding new player and return reference to handler
def addPlayer(index, websocket):
    for position in map_positions:
        if not position[3]:
            player = Player(index, websocket, position[0], position[1], position[2])
            connected.append(player)
            position[3] = True
            position[4] = index
            return player
    return None

#   # Handle logic of removing players and return results
def delPlayer(player):
    for position in map_positions:
        if position[3] and position[4] == player.i:
            position[3] = False                     
            position[4] = -1
            return True
    return False

#   # Prepare map positions and facing angle based on amount of clients - Algebra
def prepare_map():
    radius = 200.0
    angle = 0.0
    for i in range(MAX_PLAYERS):
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        direction = angle - math.pi/2
        print(" {:3f}, {:3f}    ->  {:3f}".format(x,y,angle))
        map_positions.append([x,y,direction,False, -1])
        angle += float(math.pi*2 / float(MAX_PLAYERS))
        

#   # Run
def run():
    try:
        start_server = websockets.serve(handler, HOSTNAME, PORT)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("Ctrl C")
        sys.exit()
        
#   # Where it all begins
if __name__ == '__main__':
    prepare_map()
    run()