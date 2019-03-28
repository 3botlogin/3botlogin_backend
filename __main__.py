#!/usr/bin/env python3
from flask import Flask, Response, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import time

app = Flask(__name__)
sio = SocketIO(app)
CORS(app, resources=r'/api/*')

users = []
login_attempts = []


def findUser(query, search_for="double_name"):
    print('Search for', query)
    for u in users:
        if u.get(search_for) == query:
            print('Found', u)
            return u
    return None


def find_loggin_attempt(query, search_for="state"):
    print('Search for', query)
    for la in login_attempts:
        if la.get(search_for) == query:
            print('Found', la)
            return la
    return None


@sio.on('connect')
def connect_handler():
    print('Connected!')


@sio.on('identify')
def identification_handler(data):
    print('')
    print('< identify', data)
    sid = request.sid
    print(data.get('doubleName'))
    print (sid)
    if any(data.get('doubleName') in user.get('double_name') for user in users):
        print('> sending nameknown')
        user = findUser(data.get('doubleName'))
        print('found user', user)
        user['sid'] = sid
        emit('nameknown')
    else:
        print('> sending namenotknown')
        emit('namenotknown')
        print('- Adding to array')
        users.append({'double_name': data.get('doubleName'), 'sid': sid})
    print('')


@sio.on('register')
def registration_handler(data):
    print('')
    print('< register', data)
    user = findUser(data.get('doubleName'))
    user['public_key'] = data.get('publicKey')
    user['email'] = data.get('email')
    print('')


@sio.on('login')
def login_handler(data):
    print('')
    print('< login', data)
    login_attempts.append({
        'double_name': data.get('doubleName'),
        'state': data.get('state'),
        'timestamp': time.time(),
        'scanned': False
    })
    print(find_loggin_attempt(data.get('state')))
    print(login_attempts)
    # if !data.get('firstTime')
    #     # TODO: send notification
    print('')

# TOOD: Register deviceID for user
@app.route('/api/flag', methods=['POST'])
def flag_handler():
    print('')
    body = request.get_json()
    print('< flag', body)
    user = find_loggin_attempt(body.get('hash'))
    if user:
        print('user', user)
        user['scanned'] = True
        sio.emit('scannedFlag', room=user.get('sid'))
    response = Response("bla")
    return response


@app.route('/api/sign', methods=['POST'])
def sign_handler():
    print('')
    body = request.get_json()
    print('< sign', body)
    user = find_loggin_attempt(body.get('hash'))
    if user:
        print('user', user)
        user['singedStateHash'] = body.get('signedHash')
        sio.emit('signed', body.get('signedHash'), room=user.get('sio'))
    return Response("K")


@app.route('/api/verify', methods=['POST'])
def verify_handler():
    print('')
    body = request.get_json()
    print('< verify', body)
    return Response("K")

app.run(host='0.0.0.0', port= 5000)
