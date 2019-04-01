import sqlite3
from sqlite3 import Error

# create a database connection to a SQLite database
def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
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

def insert_user(conn,insert_user_sql):
    try:
        c = conn.cursor()
        c.execute(insert_user_sql)
    except Error as e:
        print(e)
def select_all(conn,select_all_users):
    try:
        c = conn.cursor()
        c.execute(select_all_users)
        rows = c.fetchall()
 
        for row in rows:
            print(row)
    except Error as e:
        print(e)
def create_db(conn):
    #create user table statement
    sql_create_auth_table = """CREATE TABLE IF NOT EXISTS auth (double_name text NOT NULL,state_hash text NOT NULL,timestamp text NOT NULL,scanned INTEGER NOT NULL,singed_statehash text NOT NULL);"""
    #create auth table statement
    sql_create_user_table = """CREATE TABLE IF NOT EXISTS users (double_name text NOT NULL,email text NOT NULL,public_key text NOT NULL,device_id text NOT NULL); """
    if conn is not None:
        #create auth table
        create_table(conn, sql_create_auth_table)
        #create user table
        create_table(conn, sql_create_user_table)
    else:
        print("Error! cannot create the database connection.")
def main():
    #connection db
    #set other path --> now: default path in project (PATH/<name>.db)
    conn = create_connection("pythonsqlite.db")
    #create user table statement
    sql_create_user_table = """CREATE TABLE IF NOT EXISTS auth (double_name text NOT NULL,state_hash text NOT NULL,timestamp text NOT NULL,scanned INTEGER NOT NULL,singed_statehash text NOT NULL);"""
    #create auth table statement
    sql_create_auth_table = """CREATE TABLE IF NOT EXISTS users (double_name text NOT NULL,email text NOT NULL,public_key NOT NULL,device_id text NOT NULL); """
    #test insert user statement
    insert_user_sql = """INSERT INTO users (double_name,email,public_key,device_id) VALUES ('massimo.renson','massimo.renson@hotmail.com','G1gcbyeTnR2i...H8_3yV3cuF','abc');"""
    #test select all from users statement
    select_all_users = """SELECT * FROM users;"""
    if conn is not None:
        #create auth table
        create_table(conn, sql_create_auth_table)
        #create user table
        create_table(conn, sql_create_user_table)
        #test insert user
        insert_user(conn, insert_user_sql)
        #test select all users
        select_all(conn,select_all_users)
    else:
        print("Error! cannot create the database connection.")

''' if __name__ == '__main__':
    main() '''
