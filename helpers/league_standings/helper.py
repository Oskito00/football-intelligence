def find_team_standing(team_id, league_info):
    """Helper to find team by ID assuming team_id is at index 0"""
    return next((i for i, t in enumerate(league_info) if t[0] == team_id), None)

def save_to_standings_history(conn, standings_history):
    """Function to save a list of dictionaries to the league_standings_history table
    
    Args:
        conn (sqlite3.Connection): The database connection object.
        standings_history (list): A list of dictionaries, where each dictionary is a row to be inserted into the league_standings_history table.
    """

    cursor = conn.cursor()
    cursor.executemany("INSERT INTO league_standings_history (match_id, home_standing, home_matches_played, home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_goal_difference, home_points, away_standing, away_matches_played, away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_goal_difference, away_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", standings_history)
    conn.commit()
    cursor.close()

def upsert_into_standings(conn, home_team_id, away_team_id, home_team_stats, away_team_stats, competition_season_id, home_score, away_score):
    """Function to upsert a teams stats in the stnadings table based on a match
    
    Args:
        conn (sqlite3.Connection): The database connection object.
        home_team_info (list): A list of the home team's stats.
        away_team_info (list): A list of the away team's stats.
        competition_season_id (str): The competition season ID.
        home_score (int): The home team's score.
        away_score (int): The away team's score.
    """

    home_team_stats, away_team_stats = find_new_stats(home_team_stats, away_team_stats, home_score, away_score)
    team_data = [[home_team_id, competition_season_id] + home_team_stats, [away_team_id, competition_season_id] + away_team_stats]

    query = """
    INSERT INTO league_standings (
        team_id, competition_season_id, matches_played, wins, draws, losses, 
        goals_for, goals_against, goal_difference, points
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(team_id, competition_season_id) DO UPDATE SET
        matches_played = excluded.matches_played,
        wins = excluded.wins,
        draws = excluded.draws,
        losses = excluded.losses,
        goals_for = excluded.goals_for,
        goals_against = excluded.goals_against,
        goal_difference = excluded.goal_difference,
        points = excluded.points
    """

    with conn:  # Auto-commits transaction
        conn.executemany(query, team_data)

def find_new_stats(home_team_stats, away_team_stats, home_score, away_score):
    """Helper to find the teams new stats after analysing a match.

    Eg. Team A goals_for before match = 10, Team A scores 2 goals in the match, Team A goals_for after match = 12
    
    Args:
        home_team_stats (list): A list of the home team's stats.
        away_team_stats (list): A list of the away team's stats.
        home_score (int): The home team's score in the match.
        away_score (int): The away team's score in the match.
    """
    home_matches_played = home_team_stats[1] + 1 #always add 1 to matches played
    away_matches_played = away_team_stats[1] + 1

    home_wins = home_team_stats[2] + (1 if home_score > away_score else 0) # depends if home team won
    home_draws = home_team_stats[3] + (1 if home_score == away_score else 0)
    home_losses = home_team_stats[4] + (1 if home_score < away_score else 0)

    away_wins = away_team_stats[2] + (1 if away_score > home_score else 0)
    away_draws = away_team_stats[3] + (1 if away_score == home_score else 0)
    away_losses = away_team_stats[4] + (1 if away_score < home_score else 0)

    home_goals_for = home_team_stats[5] + home_score # depends on how many goals home team scored
    away_goals_for = away_team_stats[5] + away_score

    home_goals_against = home_team_stats[6] + away_score
    away_goals_against = away_team_stats[6] + home_score

    home_goal_difference = home_team_stats[7] + (home_score - away_score)
    away_goal_difference = away_team_stats[7] + (away_score - home_score)

    home_points = home_team_stats[8] + (3 if home_score > away_score else 1 if home_score == away_score else 0)
    away_points = away_team_stats[8] + (3 if away_score > home_score else 1 if away_score == home_score else 0)

    home_team_stats = [home_matches_played, home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_goal_difference, home_points]
    away_team_stats = [away_matches_played, away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_goal_difference, away_points]

    return home_team_stats, away_team_stats