def find_team_standing(team_id, league_info):
    """Helper to find team by ID assuming team_id is at index 0"""
    return next((i for i, t in enumerate(league_info) if t[0] == team_id), None)

def save_to_standings_history(conn, standings_history):
    #This function should save to a league_standings_history table.
    # The parameter is a list of lists, where each list is [match_id, home_team_info, away_team_info]
    # The columns should be match_id, home_standing, home_matches_played, home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_goal_difference, home_points, away_standing, away_matches_played, away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_goal_difference, away_points
    # the table has already been created

    print

    cursor = conn.cursor()
    cursor.executemany("INSERT INTO league_standings_history (match_id, home_standing, home_matches_played, home_wins, home_draws, home_losses, home_goals_for, home_goals_against, home_goal_difference, home_points, away_standing, away_matches_played, away_wins, away_draws, away_losses, away_goals_for, away_goals_against, away_goal_difference, away_points) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", standings_history)
    conn.commit()
    cursor.close()
