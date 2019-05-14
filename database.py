import sqlite3
from sqlite3 import Error
from flask import g
from datetime import datetime, timedelta
import time
# create a database connection to a SQLite database
def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        return conn
    except Error as e:
        print(e)

    return None

# create table users
def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

  
# setting user doublename, email & public key
def insert_user(conn,insert_user_sql,*params):
    try:
        c = conn.cursor()
        if len(params)==4:
            c.execute(insert_user_sql,(params[0],params[1],params[2],params[3]))
            conn.commit()
    except Error as e:
        print(e)

# setting login attempt double name, state hash, timestamp & scanned
def insert_auth(conn,insert_user_sql,dn,state,ts,s, data):
    delete_auth_for_user(conn,dn)
    try:
        c = conn.cursor()
        c.execute(insert_user_sql,(dn,state,ts,s, data))
        conn.commit()
    except Error as e:
        print(e)

def delete_auth_for_user(conn, double_name):
    try:
        delete_sql = 'DELETE from auth WHERE double_name=? AND singed_statehash IS NULL;'
        c = conn.cursor()
        c.execute(delete_sql, (double_name,))
        conn.commit()
    except Error as e:
        print(e)
# some printing for testing
def select_all(conn,select_all_users):
    try:
        c = conn.cursor()
        c.execute(select_all_users)
        rows = c.fetchall()

        for row in rows:
            print(row)
    except Error as e:
        print(e)

# get double name obj by hqsh 
def getUserByHash(conn,hash):
    find_statement="SELECT * FROM auth WHERE state_hash=? LIMIT 1;"
    try:
        c = conn.cursor()
        c.execute(find_statement,(hash,))
        return c.fetchone()
    except Error as e:
        print(e)

# update device id from user obj
def update_user(conn,update_sql,*params):
    try:
        c = conn.cursor()
        if len(params)==2:
            c.execute(update_sql,(params[0],params[1]))
            conn.commit()
        elif len(params)==4:
            c.execute(update_sql,(params[0],params[1],params[2],params[3]))
            conn.commit()
    except Error as e:
        print(e)

# update signed hash from auth obj
def update_auth(conn, update_sql, singed_statehash, data, double_name):
    try:
        c = conn.cursor()
        c.execute(update_sql,(singed_statehash,data,double_name))
        conn.commit()
    except Error as e:
        print(e)

# get use obj ny name       
def getUserByName(conn,double_name):
    find_statement="SELECT * FROM users WHERE double_name=? LIMIT 1;"
    try:
        c = conn.cursor()
        c.execute(find_statement,(double_name,))
        return c.fetchone()
    except Error as e:
        print(e)

#get auth obj by state hash
def getAuthByHash(conn, hash):
    find_statement="SELECT * FROM auth WHERE state_hash=? LIMIT 1;"
    try:
        c = conn.cursor()
        c.execute(find_statement,(hash,))
        return c.fetchone()
    except Error as e:
        print(e)

# get auth obj by deviceId 
def getAuthByDoubleName(conn, doublename):
    try:
        c = conn.cursor()
        find_auth_statement="SELECT * FROM auth WHERE double_name=? AND singed_statehash IS NULL LIMIT 1;"
        c.execute(find_auth_statement,(doublename,))
        auth = c.fetchone()

        print(auth)
        if auth and datetime.now() < datetime.strptime(auth[2], '%Y-%m-%d %H:%M:%S.%f') + timedelta(minutes=10) :
            return auth
        else:
            return None
    except Error as e:
        print(e)

# db init making tables users & auth(=login attempts)
def create_db(conn):
    #create user table statement
    sql_create_auth_table = """CREATE TABLE IF NOT EXISTS auth (double_name text NOT NULL,state_hash text NOT NULL, timestamp text NOT NULL,scanned INTEGER NOT NULL,singed_statehash text NULL, data text NULL);"""
    #create auth table statement
    sql_create_user_table = """CREATE TABLE IF NOT EXISTS users (double_name text NOT NULL,sid text NULL,email text NULL,public_key text NULL,device_id text NULL); """
    if conn is not None:
        #create auth table
        create_table(conn, sql_create_auth_table)
        #create user table
        create_table(conn, sql_create_user_table)
    else:
        print("Error! cannot create the database connection.")


#main() is only for testing purposes
def main():
    # #connection db
    # #set other path --> now: default path in project (PATH/<name>.db)
    print('<testing environment>')
    conn = create_connection("pythonsqlite.db")
    create_db(conn)
    
    
if __name__ == '__main__':
    main()
