#!/usr/bin/env python3
from flask import Flask, Response, request, json
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import nacl.signing
import nacl.encoding
import binascii
import struct
import base64
from pyfcm import FCMNotification
import configparser
import database as db

conn = db.create_connection("pythonsqlite.db") #connection
db.create_db(conn) # create tables

print(conn)

config = configparser.ConfigParser()
config.read('config.ini')
push_service = FCMNotification(api_key=config['DEFAULT']['API_KEY'])

app = Flask(__name__)
sio = SocketIO(app)
CORS(app, resources={r"*": {"origins": ["*"]}})

@sio.on('connect')
def connect_handler():
    print('Connected!')


@sio.on('identify')
def identification_handler(data):
    print('')
    print('< identify', data)
    sid = request.sid
    user = db.getUserByName(conn,data.get('doubleName').lower())
    print("-------->",user)
    if user:
        print('> sending nameknown')
        print('found user', user)
        update_sql="UPDATE users SET sid=?  WHERE double_name=?;"
        db.update_user(conn,update_sql,sid,user[0])
        emit('nameknown')
    else:
        print('> sending namenotknown')
        emit('namenotknown')
        print('- Adding to array')
        insert_user_sql = "INSERT INTO users (double_name,sid) VALUES (?,?);"
        db.insert_user(conn,insert_user_sql,data.get('doubleName').lower(),sid)
        
    print('')


@sio.on('register')
def registration_handler(data):
    print('')
    print('< register', data)
    print('')
    doublename=data.get('doubleName').lower()
    email=data.get('email')
    publickey=data.get('publicKey')
    update_sql="UPDATE users SET email=?,public_key=?  WHERE double_name=?;"
    db.update_user(conn,update_sql,email,publickey,doublename)

# TODO: Add requested data to db
@sio.on('login')
def login_handler(data):
    print('')
    print('< login', data)
    if data.get('firstTime') == False:
        user = db.getUserByName(conn,data.get('doubleName').lower())
        push_service.notify_single_device(registration_id=user[4], message_title='Finish login', message_body='Tap to finish login', data_message=data, click_action='FLUTTER_NOTIFICATION_CLICK' )
    print('')
    insert_auth_sql="INSERT INTO auth (double_name,state_hash,timestamp,scanned,data) VALUES (?,?,?,?,?);"
    db.insert_auth(conn,insert_auth_sql,data.get('doubleName').lower(),data.get('state'), datetime.now(),0, json.dumps(data))

@sio.on('resend')
def resend_handler(data):
    print('')
    print('< resend', data)
    user = db.getUserByName(conn,data.get('doubleName').lower())
    push_service.notify_single_device(registration_id=user[4], message_title='Finish login', message_body='Tap to finish login', data_message=data, click_action='FLUTTER_NOTIFICATION_CLICK' )
    print('')

@app.route('/api/forcerefetch', methods=['GET'])
def force_refetch_handler():
    print('')
    data = request.args
    print('< force refetch', data)
    if (data == None): return Response("Got no data", status=400)
    print('hash', data['hash'])
    loggin_attempt = db.getAuthByHash(conn, data['hash'])
    print(loggin_attempt)
    if (loggin_attempt != None):
        data = {"scanned": loggin_attempt[3], "signed": loggin_attempt[4]}
        response = app.response_class(
            response=json.dumps(data),
            mimetype='application/json'
        )
        print(data)
        return response
        

@app.route('/api/flag', methods=['POST'])
def flag_handler():
    print('')
    body = request.get_json()
    print('< flag', body)
    loggin_attempt = db.getAuthByHash(conn,body.get('hash'))
    print(loggin_attempt)
    if loggin_attempt:

        update_sql="UPDATE users SET device_id=?  WHERE device_id=?;"
        db.update_user(conn,update_sql,'',body.get('deviceId'))

        user = db.getUserByName(conn,loggin_attempt[0])
        update_sql="UPDATE auth SET scanned=?  WHERE double_name=?;"
        db.update_auth(conn,update_sql,1,'',loggin_attempt[0])
        update_sql="UPDATE users SET device_id =?  WHERE double_name=?;"
        db.update_user(conn,update_sql,body.get('deviceId'),loggin_attempt[0])
        sio.emit('scannedFlag', room=user[1])
    
        device_id=body.get('deviceId')
        update_user_sql="UPDATE users SET device_id =?  WHERE double_name=?;"
        db.update_user(conn,update_user_sql, device_id, user[0])
        return Response("Ok")
    else:
        return Response('User not found', status=404)


@app.route('/api/sign', methods=['POST'])
def sign_handler():
    print('')
    body = request.get_json()
    print('< sign', body)
    login_attempt = db.getAuthByHash(conn,body.get('hash'))
    if login_attempt != None:
        print(login_attempt)
        user = db.getUserByName(conn,login_attempt[0])
        print(user)
        update_sql="UPDATE auth SET singed_statehash =?, data=?  WHERE state_hash=?;"
        db.update_auth(conn,update_sql,body.get('signedHash'), json.dumps(body.get('data')),body.get('hash'))
        login_attempt = db.getAuthByHash(conn,body.get('hash'))
        print(login_attempt)
        sio.emit('signed', {
            'signedHash': body.get('signedHash'),
            'data': body.get('data')
        }, room=user[1])      
        return Response("Ok")
    else:
        return Response("Something went wrong", status=500)


@app.route('/api/attempts/<doublename>', methods=['GET'])
def get_attempts_handler(doublename):
    print('')
    print('< get attempts', doublename.lower())
    login_attempt = db.getAuthByDoubleName(conn, doublename.lower())
    print('>', login_attempt)
    if (login_attempt is not None):
        print('not none')
        response = app.response_class(
            response=json.dumps(json.loads(login_attempt[5])),
            mimetype='application/json'
        )
        return response
    else:
        print('is none')
        return Response("No login attempts found", status=204)


@app.route('/api/verify', methods=['POST'])
def verify_handler():
    print('')
    body = request.get_json()
    print('< verify', body)
    user = db.getUserByName(conn,body.get('username'))
    login_attempt = db.getAuthByHash(conn,body.get('hash'))
    if user and login_attempt:
        requested_datetime = datetime.strptime(login_attempt[2], '%Y-%m-%d %H:%M:%S.%f')
        max_datetime = requested_datetime + timedelta(minutes=10)
        if requested_datetime < max_datetime:
            public_key = base64.b64decode(user[3])
            print(login_attempt)
            signed_hash = base64.b64decode(login_attempt[4])
            original_hash = login_attempt[1]
            try:
                bytes_signed_hash = bytes(signed_hash)
                bytes_original_hash = bytes(original_hash, encoding='utf8')
                verify_key = nacl.signing.VerifyKey(public_key.hex(), encoder=nacl.encoding.HexEncoder)
                verify_key.verify(bytes_original_hash, bytes_signed_hash)
                return Response("Ok")
            except:
                return Response("Sinature invalid", status=400)
        else:
            return Response("You are too late", status=400)

    else:
        return Response("Oops.. user or loggin attempt not found", status=404)

@app.route('/api/users/<doublename>', methods=['GET'])
def get_user_handler(doublename):
    print('')
    print('< get doublename', doublename.lower())
    user = db.getUserByName(conn, doublename.lower())
    print('>', user)
    if (user is not None):
        print('not none')
        data = {
            "doublename": doublename.lower(),
            "publicKey": user[3]
        }
        response = app.response_class(
            response=json.dumps(data),
            mimetype='application/json'
        )
        print(data)
        return response
    else:
        print('is none')
        return Response(None)

app.run(host='0.0.0.0', port=5000)
