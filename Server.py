#from ordered_set import OrderedSet as oset
from sortedcontainers import SortedSet as oset
import sys
import math
import json
import asyncio
import websockets
from Client import Client

connected = list()
available_index = oset([0,1,2,3,4,5,6,7,8,9])
map_positions = []
max_players = 10

port = 1501

class Player(Client):
    def __init__(self, i, websocket, x, y, a):
        Client.__init__(self,i, websocket)
        self.x = x
        self.y = y
        self.a = a

    def getData(self):
        return "{:.3f},{:.3f},{:.3f}".format(self.x, self.y, self.a)

def broadcast_except(player):
    recipients = list(filter(lambda p: p is not player, connected))
    message = json.dumps(
        {
            player.i: player.getData()
        }
    )
    for recipient in recipients:
        recipient.pre_send(message)


def initiate(player):
    
    message = dict(map(lambda p: (p.i, p.getData()), connected))
    message["Player"] = message.pop(player.i)
    player.json_prepare(message)
    broadcast_except(player)

def message_handle(player, websocket, message):
    if player is not None:
        data = map(float,message.split(','))
        print("Player {} data {}".format(player.i, list(data)))


async def handler(websocket, path):
    global index
    if len(connected) >= max_players-1:
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

def addPlayer(index, websocket):
    for position in map_positions:
        if not position[3]:
            player = Player(index, websocket, position[0], position[1], position[2])
            connected.append(player)
            position[3] = True
            position[4] = index
            return player
    return None

def delPlayer(player):
    for position in map_positions:
        if position[3] and position[4] == player.i:
            position[3] = False                     
            position[4] = -1
            return True
    return False

def prepare_map():
    radius = 200.0
    angle = 0.0
    for i in range(max_players):
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        direction = angle-math.pi/2.0
        map_positions.append([x,y,direction,False, -1])
        angle += 360 / max_players

def run():
    try:
        start_server = websockets.serve(handler, '192.168.15.2', port)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        print("Ctrl C")
        sys.exit()
        

if __name__ == '__main__':
    prepare_map()
    run()