# Take matches that have not already been processed and add them to the h2h table

import sqlite3
import json

def select_matches_to_process(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT match_id, home_team_id, away_team_id, home_score, away_score, start_time, match_status FROM matches WHERE home_score IS NOT NULL AND away_score IS NOT NULL AND match_status != 'not_started' AND h2h_processed = 0")
    matches = cursor.fetchall()  # Convert cursor to a list of results
    return matches

def process_h2h_table(conn):
    cursor = conn.cursor()
    matches = select_matches_to_process(conn)
    print("Length of matches: ", len(matches))
    for match in matches:
        print("Processing match: ", match[0])
        match_id = match[0]
        home_team_id = match[1]
        away_team_id = match[2]
        home_score = match[3]
        away_score = match[4]
        start_time = match[5]
        
        # Ensure the order is lower team first, higher team second
        if home_team_id < away_team_id:
            team1_id = home_team_id
            team2_id = away_team_id
        else:
            team1_id = away_team_id
            team2_id = home_team_id
            
        # Check if the h2h table already has an entry for these two teams
        result = cursor.execute("SELECT COUNT(*) FROM h2h WHERE team1_id = ? AND team2_id = ?", 
                               (team1_id, team2_id)).fetchone()
        exists = result[0]
        
        if exists == 1:
            # Get the current matches JSON
            current_matches = cursor.execute("SELECT matches FROM h2h WHERE team1_id = ? AND team2_id = ?", 
                                          (team1_id, team2_id)).fetchone()[0]
            
            # Make sure start_time is a string for JSON
            if start_time is not None and not isinstance(start_time, str):
                start_time = str(start_time)
                
            # Create new match JSON
            match_data = {
                "match_id": match_id,
                "home_score": home_score,
                "away_score": away_score,
                "start_time": start_time
            }
            
            # Parse current matches, add new match, and stringify
            try:
                matches_list = json.loads(current_matches)
                matches_list.append(match_data)
                new_matches_json = json.dumps(matches_list)
            except (json.JSONDecodeError, TypeError):
                # If current JSON is invalid, create a new array with just this match
                new_matches_json = json.dumps([match_data])
            
            # Update with the new JSON
            cursor.execute("UPDATE h2h SET matches = ?, last_updated = CURRENT_TIMESTAMP WHERE team1_id = ? AND team2_id = ?", 
                          (new_matches_json, team1_id, team2_id))
        else:
            # If there is no entry, create a new one with the match data
            match_data = [{
                "match_id": match_id,
                "home_score": home_score,
                "away_score": away_score,
                "start_time": str(start_time) if start_time is not None else None
            }]
            match_json = json.dumps(match_data)
            cursor.execute("INSERT INTO h2h (team1_id, team2_id, matches, last_updated) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", 
                          (team1_id, team2_id, match_json))
        
        # Mark the match as processed for h2h
        cursor.execute("UPDATE matches SET h2h_processed = 1 WHERE match_id = ?", (match_id,))
    
    # Commit the transaction
    conn.commit()
    print("H2H table processing complete")

if __name__ == "__main__":
    conn = sqlite3.connect("v2db.sqlite")
    process_h2h_table(conn)