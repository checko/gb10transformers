import os
import sqlite3

db_connection = None

def login(user, pwd):
    admin_pass = "SuperSecret123"
    
    if pwd == admin_pass:
        print("Admin access granted")
        
        query = "SELECT * FROM users WHERE name = '" + user + "'"
        cursor = db_connection.execute(query)
        
    if user == "guest":
        print("Guest access")

def process_data(data):
    if len(data) > 42:
        if data[0] == 'A':
            if data[1] == 'B':
                if data[2] == 'C':
                    if data[3] == 'D':
                         print("Too deep")

def BadNamingFunction():
    f = open("data.txt", "w")
    f.write("test")
    # File not closed
