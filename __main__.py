#!/usr/bin/env python
from aiohttp import web
import socketio

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

def connect_handler(id, msg):
    print(f'> Someone connected: {id}')


sio.on('connect', connect_handler)

web.run_app(app)
