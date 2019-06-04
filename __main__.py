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

@sio.on('checkname')
def checkname_handler(data):
    print('')
    print('< checkname', data)
    sid = request.sid
    user = db.getUserByName(conn,data.get('doubleName').lower())
    print("-------->",user)
    if user:
        emit('nameknown')
    else:
        emit('namenotknown')
    print('')

@sio.on('register')
def registration_handler(data):
    print('')
    print('< register', data)
    print('')
    doublename=data.get('doubleName').lower()
    email=data.get('email')
    sid = request.sid
    publickey=data.get('publicKey')
    user = db.getUserByName(conn,doublename)
    if (user is None) :
        update_sql="INSERT into users (double_name, sid, email, public_key) VALUES(?,?,?,?);"
        db.insert_user(conn,update_sql,doublename, sid, email ,publickey)

@sio.on('login')
def login_handler(data):
    print('')
    print('< login', data)
    data['type'] = 'login'

    sid = request.sid
    user = db.getUserByName(conn,data.get('doubleName').lower())
    if user:
        print('found user', user)
        update_sql="UPDATE users SET sid=?  WHERE double_name=?;"
        db.update_user(conn,update_sql,sid,user[0])

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
    data['type'] = 'login'
    push_service.notify_single_device(registration_id=user[4], message_title='Finish login', message_body='Tap to finish login', data_message=data, click_action='FLUTTER_NOTIFICATION_CLICK' )
    print('')

@app.route('/api/forcerefetch', methods=['GET'])
def force_refetch_handler():
    print('')
    data = request.args
    print('< force refetch', data)
    if (data == None): return Response("Got no data", status=400)
    print('hash', data['hash'])
    loggin_attempt = db.getAuthByStateHash(conn, data['hash'])
    print(loggin_attempt)
    if (loggin_attempt != None):
        data = {"scanned": loggin_attempt[3], "signed": loggin_attempt[4]}
        response = app.response_class(
            response=json.dumps(data),
            mimetype='application/json'
        )
        print(data)
        return response
    else:
        return Response()
        

@app.route('/api/flag', methods=['POST'])
def flag_handler():
    print('')
    body = request.get_json()
    print('< flag', body)
    login_attempt = db.getAuthByStateHash(conn,body.get('hash'))
    user = db.getUserByName(conn,login_attempt[0])
    if login_attempt and user:
        print("login_attempt " + json.dumps(login_attempt))
        print("user  a  " + json.dumps(user))
        if body.get('isSigned') is None:
            print('its not signed')
            update_sql="UPDATE users SET device_id=?  WHERE device_id=?;"
            db.update_user(conn,update_sql,'',body.get('deviceId'))

            user = db.getUserByName(conn,login_attempt[0])
            print(user)
            update_sql="UPDATE auth SET scanned=?, data=?  WHERE double_name=?;"
            db.update_auth(conn,update_sql,1,'',login_attempt[0])
            print('update device id')
            update_sql="UPDATE users SET device_id =?  WHERE double_name=?;"
            db.update_user(conn,update_sql,body.get('deviceId'),login_attempt[0])
            
            sio.emit('scannedFlag', { 'scanned': True }, room=user[1])
            return Response("Ok")
        else:  
            try:
                public_key = base64.b64decode(user[3])
                print('public_key ')
                signed_device_id = base64.b64decode(body.get('deviceId'))
                print('signed_device_id ')
                bytes_signed_device_id = bytes(signed_device_id)
                print('bytes_signed_device_id ')
                verify_key = nacl.signing.VerifyKey(public_key.hex(), encoder=nacl.encoding.HexEncoder)
                print('VerifyKey ok')
                verified_device_id = verify_key.verify(bytes_signed_device_id)
                print('Validation ok')
                if verified_device_id:
                    verified_device_id = verified_device_id.decode("utf-8")                 
                    print("verified_device_id " + verified_device_id)

                    update_sql="UPDATE users SET device_id=?  WHERE device_id=?;"
                    db.update_user(conn,update_sql,'',verified_device_id)

                    update_sql="UPDATE auth SET scanned=?, data=?  WHERE double_name=?;"
                    db.update_auth(conn,update_sql,1,'',login_attempt[0])

                    print('update device id for '+ login_attempt[0])
                    update_sql="UPDATE users SET device_id =?  WHERE double_name=?;"
                    db.update_user(conn,update_sql,verified_device_id,login_attempt[0])
                    
                    sio.emit('scannedFlag', { 'signed': True }, room=user[1])
                return Response("Ok")
            except Exception as e:
                print("OOPS")
                print(e)
                print("OOPS")
                return Response("Sinature invalid", status=400)
    else:
        return Response('User not found', status=404)


@app.route('/api/sign', methods=['POST'])
def sign_handler():
    print('')
    body = request.get_json()
    print('< sign', body)
    login_attempt = db.getAuthByStateHash(conn,body.get('hash'))
    if login_attempt != None:
        print(login_attempt)
        user = db.getUserByName(conn,login_attempt[0])
        print(user)
        update_sql="UPDATE auth SET singed_statehash =?, data=?  WHERE state_hash=?;"
        db.update_auth(conn,update_sql,body.get('signedHash'), json.dumps(body.get('data')),body.get('hash'))
        sio.emit('signed', {
            'signedHash': body.get('signedHash'),
            'data': body.get('data'),
            'selectedImageId': body.get('selectedImageId')
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
    login_attempt = db.getAuthByStateHash(conn,body.get('hash'))
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
        return Response('User not found', status=404)

@app.route('/api/users/<doublename>/emailverified', methods=['post'])
def set_email_verified_handler(doublename):
    print('')
    print('< get user', doublename.lower())
    user = db.getUserByName(conn,doublename.lower())
    push_service.notify_single_device(registration_id=user[4], message_title='Email verified', message_body='Thanks for verifying your email', data_message={'type': 'email_verification'} ,click_action='EMAIL_VERIFIED')
    return Response('Ok')

@app.route('/api/minversion', methods=['get'])
def min_version_handler():
    return Response('16')

app.run(host='0.0.0.0', port=5000)
