import os
import json;
from extract_useful_match_data import extract_useful_match_data;


matches_dir = 'C:/Users/Will Boyd/InBETments Predictor/Data_Scraping/Data/raw/matches_data'
lineups_dir = 'C:/Users/Will Boyd/InBETments Predictor/Data_Scraping/Data/raw/lineups_data'

matches_files = [f for f in os.listdir(matches_dir) if f.endswith('.json')]
lineups_files = [f for f in os.listdir(lineups_dir) if f.endswith('.json')]
file_pairs = [(matches_files[i], lineups_files[i]) for i in range(len(matches_files))]

useful_data = []

for matches_file, lineups_file in file_pairs:
    if matches_file.endswith('.json'):

        print(f"Extracting from {matches_file}....");

        with open(f'{matches_dir}/{matches_file}', 'r') as f:
            raw_matches = json.load(f)
        with open(f'{lineups_dir}/{lineups_file}', 'r') as g:
            raw_lineups = json.load(g)

        extract_useful_match_data(raw_matches, raw_lineups, useful_data)
        

clean_data_json = json.dumps(useful_data, indent=4)

with open('C:/Users/Will Boyd/InBETments Predictor/Data_Scraping/Data/clean_data.json', 'w') as h:
    h.write(clean_data_json)
    print("Data saved to clean_data.json")