import os
import mysql.connector
from converter import config

def connect_mysql():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASS,
        database=config.DB_NAME
    )
    return conn, conn.cursor(dictionary=True)

