Football Match Predictor using Sportradar API

1. Scrape lineups and matches in Data_Scraping
2. Migrate the json files to SQL database with Data_Migration/oscar_SQLite_migration/migrate_jsons_to_sql.py
3. Extract features from data.
4. calculate_elos create elo history and updated elo_ratings. TODO: Just need to make it only use matches that haven't been processed yet...
5. process_h2h_table processes matches and creates the h2h table for extracting features...
6. form

#Contributors
Oscar Alberigo, William Boyd

