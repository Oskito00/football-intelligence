import os
from dotenv import load_dotenv
import psycopg2
load_dotenv()

###### Connecting the postgres  #######################################
postgres_port = os.getenv("POSTGRES_PORT")
postgres_password = os.getenv("POSTGRES_PASSWORD")

try:
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password=postgres_password,
        host= "localhost",
        port = postgres_port
    )

    print("successfully connected")

except Exception as e:
    print(e)

conn
########## ^^^ Connecting to postgres ########################################