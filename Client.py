import sys
import math
import json
import asyncio
import websockets

class GraceFuture(asyncio.Future):
    def __init__(self):
        asyncio.Future.__init__(self)

    def set_result_default(self, result):
        if not self.done():
            self.set_result(result)
        return self.result()

class Client:

    def __init__(self, i, ws):
        self.i = i
        self.websocket = ws
        self.alive = True
        self.future = GraceFuture()

    async def produce(self):
        await self.future
        result = self.future.result()
        self.future = GraceFuture()
        return result

    def pre_send(self, message):
        self.future.set_result_default([]).append(message)

    def json_prepare(self, message):
        self.pre_send(json.dumps(message))