#!/usr/bin/env python
from aiohttp import web
import socketio
import time

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

users = [{
    'double_name': 'ivan.coene',
    'public_key': 'abc123'
}]
login_attempts = [{
    'double_name': 'ivan.coene',
    'hash': 'aaa',
    'timestamp': time.time(),
    'scanned': False
}]


@sio.on('connect')
def connect_handler(id, data):
    print('Connected!')


@sio.on('identify')
async def identification_handler(id, data):
    print('')
    print('< identify', data)
    if any(data.get('doubleName') in user.get('double_name') for user in users):
        print('> sending nameknown')
        await sio.emit('nameknown')
    else:
        print('> sending namenotknown')
        await sio.emit('namenotknown')
        print('- Adding to array')
        users.append({'double_name': data.get('doubleName')})
    print('')


@sio.on('register')
async def registration_handler(id, data):
    print('')
    print('< register', data)
    user = next(user for user in users if user.get(
        'double_name') == data.get('doubleName'))
    user['public_key'] = data.get('publicKey')
    user['email'] = data.get('email')
    print(users)
    print('')


@sio.on('login')
async def login_handler(id, data):
    print('')
    print('< login', data)
    login_attempts.append({
        'double_name': data.get('doubleName'),
        'state': data.get('state'),
        'timestamp': time.time(),
        'scanned': False
        })
    print(login_attempts)
    # if !data.get('firstTime') 
    #     # TODO: send notification
    print('')

web.run_app(app)
