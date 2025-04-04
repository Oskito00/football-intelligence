import os
import json;
from extract_useful_match_data import extract_useful_match_data;


## Defining the raw file locations
matches_dir = 'C:/Users/Will Boyd/InBETments Predictor/Data/raw/matches_data'
lineups_dir = 'C:/Users/Will Boyd/InBETments Predictor/Data/raw/lineups_data'

## Creating a list of file pairs --- corresponding matches and lineups data
matches_files = [f for f in os.listdir(matches_dir) if f.endswith('.json')]
lineups_files = [f for f in os.listdir(lineups_dir) if f.endswith('.json')]
file_pairs = [(matches_files[i], lineups_files[i]) for i in range(len(matches_files))]

## We will fill this list with a clean object for every match in every season in every league
useful_data = []

#### Looping through the files and extracting all information ###################
for matches_file, lineups_file in file_pairs:
    if matches_file.endswith('.json'):

        print(f"Extracting from {matches_file}....");

        with open(f'{matches_dir}/{matches_file}', 'r') as f:
            raw_matches = json.load(f)
        with open(f'{lineups_dir}/{lineups_file}', 'r') as g:
            raw_lineups = json.load(g)

        extract_useful_match_data(raw_matches, raw_lineups, useful_data)
##################################################################################

### Creating a master json file with all clean, useful data
clean_data_json = json.dumps(useful_data, indent=4)

#### Save the file to the Data folder
with open('C:/Users/Will Boyd/InBETments Predictor/Data/clean_data.json', 'w') as h:
    h.write(clean_data_json)
    print("Data saved to clean_data.json")