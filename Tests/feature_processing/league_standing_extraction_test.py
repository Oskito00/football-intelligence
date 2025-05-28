

from helpers.league_standings.helper import find_new_stats

def find_new_stats_test():
    """Unit test for find_new_stats function"""
    home_team_stats = [7,10,7,3,0,10,5,5,24]
    away_team_stats = [20,10,3,0,7,5,10,0-5,9]
    home_score = 3
    away_score = 1
    new_home_stats = find_new_stats(home_team_stats, away_team_stats, home_score, away_score)
    print(new_home_stats)
    assert new_home_stats == [11,8,3,0,13,6,7,27]