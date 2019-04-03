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

#SQlite --> problems with flask (threading) --> solution set check_same_thread=False when creating connection
#database init
conn = db.create_connection("pythonsqlite.db") #connection
db.create_db(conn) # create tables
#print tests
select_all_users = """SELECT * FROM users;"""
select_all_auth = """SELECT * FROM auth;"""

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
    #user = find_user(data.get('doubleName'))
    user = db.getUserByName(conn,data.get('doubleName'))
    print("-------->",user)
    if user:
        print('> sending nameknown')
        print('found user', user)
        print(user['sid'])
        #user['sid'] = sid
        update_sql="UPDATE users SET sid=?  WHERE double_name=?;"
        db.update_user(conn,update_sql,sid,user['double_name'])
        emit('nameknown')
    else:
        print('> sending namenotknown')
        emit('namenotknown')
        print('- Adding to array')
        users.append({'double_name': data.get('doubleName'), 'sid': sid})
        #db part
        insert_user_sql = "INSERT INTO users (double_name,sid) VALUES (?,?);"
        db.insert_user(conn,insert_user_sql,data.get('doubleName'),sid)
        
    print('')


@sio.on('register')
def registration_handler(data):
    print('')
    print('< register', data)
    user = find_user(data.get('doubleName'))
    user['public_key'] = data.get('publicKey')
    user['email'] = data.get('email')
    print('')
    #db part
    doublename=data.get('doubleName')
    email=data.get('email')
    publickey=data.get('publicKey')
    #insert_user_sql = "INSERT INTO users (double_name,email,public_key) VALUES (?,?,?);"
    #db.insert_user(conn,insert_user_sql,doublename,email,publickey)
    update_sql="UPDATE users SET email=?,public_key=?  WHERE double_name=?;"
    db.update_user(conn,update_sql,email,publickey,doublename)
    #db.select_all(conn,select_all_users)


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
        #user = find_user(data.get('doubleName'))
        user = db.getUserByName(conn,data.get('doubleName'))
        #push_service.notify_single_device(registration_id=user.get('device_id'), message_title='Finish login', message_body='Tap to finish login', data_message={ 'hash': data.get('state') }, click_action='FLUTTER_NOTIFICATION_CLICK' )
        push_service.notify_single_device(registration_id=user['device_id'], message_title='Finish login', message_body='Tap to finish login', data_message={ 'hash': data.get('state') }, click_action='FLUTTER_NOTIFICATION_CLICK' )
    print('')
    #db part
    insert_auth_sql="INSERT INTO auth (double_name,state_hash,timestamp,scanned) VALUES (?,?,?,?);"
    db.insert_auth(conn,insert_auth_sql,data.get('doubleName'),data.get('state'),datetime.datetime.now(),0)
    #db.select_all(conn,select_all_auth)

@app.route('/api/flag', methods=['POST'])
def flag_handler():
    print('')
    body = request.get_json()
    print('< flag', body)
    #loggin_attempt = find_loggin_attempt(body.get('hash')) # finding user by hash?
    loggin_attempt = db.getAuthByHash(conn,body.get('hash'))
    if loggin_attempt:
        #user = find_user(loggin_attempt.get('double_name'))
        user = db.getUserByName(conn,loggin_attempt['double_name'])
        #loggin_attempt['scanned'] = True
        update_sql="UPDATE auth SET scanned=?  WHERE double_name=?;"
        db.update_auth(conn,update_sql,1,loggin_attempt['double_name'])
        #user['device_id'] = body.get('deviceId') # device_id --> user table
        update_sql="UPDATE users SET device_id  WHERE double_name=?;"
        db.update_user(conn,update_sql,body.get('deviceId'),loggin_attempt['double_name'])
        sio.emit('scannedFlag', room=user['sid'])
        #db part
        double_name = db.getUserByHash(conn,body.get('hash'))
        device_id=body.get('deviceId')
        update_user_sql="UPDATE users SET device_id =?  WHERE double_name=?;"
        db.update_user(conn,update_user_sql,device_id,double_name)
        return Response("Ok")
    else:
        return Response('User not found', status=404)


@app.route('/api/sign', methods=['POST'])
def sign_handler():
    print('')
    body = request.get_json()
    print('< sign', body)
    #login_attempt = find_loggin_attempt(body.get('hash')) #finding user by hash?
    login_attempt = db.getAuthByHash(conn,body.get('hash'))
    if login_attempt:
        print('user', login_attempt)
        #login_attempt['singed_statehash'] = body.get('signedHash') # signed hash --> auth table
        update_sql="UPDATE auth SET singed_statehash =?  WHERE double_name=?;"
        db.update_auth(conn,update_sql,body.get('signedHash'),login_attempt['double_name'])
        sio.emit('signed', body.get('signedHash'), room=login_attempt['sid'])
        #db part
        #update_auth_sql="UPDATE auth SET singed_statehash =?  WHERE double_name=?;"
        #double_name=db.getUserByHash(conn,body.get('hash'))
        #signed_hash=body.get('signedHash')
        #db.update_auth(conn,update_auth_sql,signed_hash,double_name)
    return Response("Ok")


@app.route('/api/verify', methods=['POST'])
def verify_handler():
    print('')
    body = request.get_json()
    print('< verify', body)
    #user = find_user(body.get('username'))
    #login_attempt = find_loggin_attempt(body.get('hash'))
    user = db.getUserByName(conn,body.get('username'))
    login_attempt = db.getAuthByHash(conn,body.get('hash'))
    if user and login_attempt:
        #requested_datetime = login_attempt.get('timestamp') # obj login_attempt get timestamp
        requested_datetime = login_attempt['timestamp']
        max_datetime = requested_datetime + timedelta(minutes=10)
        if requested_datetime < max_datetime:
            #public_key = base64.b64decode(user.get('public_key')) # obj user get public key
            public_key = base64.b64decode(user['public_key'])
            #signed_hash = base64.b64decode(login_attempt.get('singed_statehash')) # obj login_attempt get signed hash
            signed_hash = base64.b64decode(login_attempt['singed_statehash'])
            #original_hash = login_attempt.get('state') # obj login_attempt get state hash
            original_hash = login_attempt['state_hash']
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


app.run(host='0.0.0.0', port=5005, debug=True)
