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
########## ^^^ Connecting to postgres ########################################

import json
## Load clean data file
with open("C:/Users/Will Boyd/InBETments Predictor/Data/APIfootball/clean_data.json", "r") as file:
    clean_data = json.load(file)


### Form a generic SQL insert query based on the columns of the match stats db
def create_insert_query(match):
    quotes_adder = []
    for key in match:
        if type(match[key])== int:
            quotes_adder.append(0)
        else:
            i=0
            while i < len(match[key]):
                symbol = match[key][i]
                if symbol == '\'':
                    match[key] = match[key][:i] + '\'' + match[key][i:]
                    i+=1
                i+=1;
                    
            quotes_adder.append("\'")
    return f'''
        INSERT INTO apifootball_stats ({", ".join(match)})
        VALUES ({", ".join([f'{quotes_adder[i] + match[key] + quotes_adder[i]}' for i, key in enumerate(match)])})
    '''

cursor = conn.cursor()
for count, match in enumerate(clean_data):
    try:
        query = create_insert_query(match)
        cursor.execute(query);
        conn.commit();

    except TypeError:
        continue

    if count % 10000 == 0:
        print(f"{count} matches uploaded.")
print("Stats uploaded to postgres!")

### 12665 out of 296123 don't have scores (~4.3%)
