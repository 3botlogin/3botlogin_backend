#!/usr/bin/env python3
from flask import Flask, Response, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import datetime
from datetime import timedelta
import nacl.signing
import nacl.encoding
import binascii
import struct
import base64
from pyfcm import FCMNotification
import configparser
import database as db

#database init
conn = db.create_connection("pythonsqlite.db") #connection
db.create_db(conn) # create tables
#test
# insert_user_sql = """INSERT INTO users (double_name,email,public_key,device_id) VALUES ('massimo.renson','massimo.renson@hotmail.com','G1gcbyeTnR2i...H8_3yV3cuF','abc');"""
# db.insert_user(conn,insert_user_sql)
# select_all_users = """SELECT * FROM users;"""
# db.select_all(conn,select_all_users)

config = configparser.ConfigParser()
config.read('config.ini')

push_service = FCMNotification(api_key=config['DEFAULT']['API_KEY'])
app = Flask(__name__)
sio = SocketIO(app)
CORS(app, resources=r'/api/*')

users = []
login_attempts = []


def find_user(query, search_for="double_name"):
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
    user = find_user(data.get('doubleName'))
    if user:
        print('> sending nameknown')
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
    user = find_user(data.get('doubleName'))
    user['public_key'] = data.get('publicKey')
    user['email'] = data.get('email')
    print('')
    insert_user_sql = "INSERT INTO users (double_name,email,public_key) VALUES ("+user.get("double_name")+","+user.get("email")+","+user.get("public_key")+");"
    db.insert_user(conn,insert_user_sql)


@sio.on('login')
def login_handler(data):
    print('')
    print('< login', data)
    login_attempts.append({
        'double_name': data.get('doubleName'),
        'state': data.get('state'),
        'timestamp': datetime.datetime.now(),
        'scanned': False
    })
    print(find_loggin_attempt(data.get('state')))
    print(login_attempts)
    if data.get('firstTime') == False:
        user = find_user(data.get('doubleName'))
        push_service.notify_single_device(registration_id=user.get('device_id'), message_title='Finish login', message_body='Tap to finish login', data_message={ 'hash': data.get('state') }, click_action='FLUTTER_NOTIFICATION_CLICK' )
    print('')
    insert_auth_sql="INSERT INTO auth (double_name,state_hash,timestamp,scanned) VALUES ("+login_attempts["double_name"]+","+login_attempts["state"]+","+login_attempts["timestamp"]+","+login_attempts["scanned"]+");"
    db.insert_user(conn,insert_auth_sql)

@app.route('/api/flag', methods=['POST'])
def flag_handler():
    print('')
    body = request.get_json()
    print('< flag', body)
    loggin_attempt = find_loggin_attempt(body.get('hash'))
    if loggin_attempt:
        user = find_user(loggin_attempt.get('double_name'))
        loggin_attempt['scanned'] = True
        user['device_id'] = body.get('deviceId')
        sio.emit('scannedFlag', room=loggin_attempt.get('sid'))
        insert_user_sql="INSERT INTO users (device_id) VALUES ("+user["device_id"]+") WHERE double_name="+user["double+name"]+";"
        db.insert_user(conn,insert_user_sql)
        return Response("Ok")
    else:
        return Response('User not found', status=404)


@app.route('/api/sign', methods=['POST'])
def sign_handler():
    print('')
    body = request.get_json()
    print('< sign', body)
    user = find_loggin_attempt(body.get('hash'))
    if user:
        print('user', user)
        user['singed_statehash'] = body.get('signedHash')
        sio.emit('signed', body.get('signedHash'), room=user.get('sio'))
        insert_auth_sql="INSERT INTO auth (singed_statehash) VALUES ("+user["singed_statehash"]+") WHERE double_name="+user["double+name"]+";"
        db.insert_user(conn,insert_auth_sql)
    return Response("Ok")


@app.route('/api/verify', methods=['POST'])
def verify_handler():
    print('')
    body = request.get_json()
    print('< verify', body)
    user = find_user(body.get('username'))
    login_attempt = find_loggin_attempt(body.get('hash'))
    if user and login_attempt:
        requested_datetime = login_attempt.get('timestamp')
        max_datetime = requested_datetime + timedelta(minutes=10)
        if requested_datetime < max_datetime:
            public_key = base64.b64decode(user.get('public_key'))
            signed_hash = base64.b64decode(
                login_attempt.get('singed_statehash'))
            original_hash = login_attempt.get('state')
            try:
                bytes_signed_hash = bytes(signed_hash)
                bytes_original_hash = bytes(original_hash, encoding='utf8')
                verify_key = nacl.signing.VerifyKey(
                    public_key.hex(), encoder=nacl.encoding.HexEncoder)
                verify_key.verify(bytes_original_hash, bytes_signed_hash)
                return Response("Ok")
            except:
                return Response("Sinature invalid", status=400)
        else:
            return Response("You are too late", status=400)

    else:
        return Response("Oops.. user or loggin attempt not found", status=404)


app.run(host='0.0.0.0', port=5005)
