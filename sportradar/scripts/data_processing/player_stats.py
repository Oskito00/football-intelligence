from datetime import datetime
import json
from typing import Dict, List, Any
import numpy as np

def initialize_player_database(conn):
    """Create necessary tables for tracking player running statistics"""
    cursor = conn.cursor()
    
    # Drop existing tables to ensure we have the correct schema
    cursor.execute("DROP TABLE IF EXISTS player_running_stats")
    
    # Create player_running_stats table
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_running_stats (
        player_id TEXT,
        player_name TEXT,
        team_id TEXT,
        position TEXT,
        start_time TEXT,
        match_id TEXT,
        
        -- The important scores
        match_importance_score REAL DEFAULT 0,  -- Score for this specific match
        overall_importance_score REAL DEFAULT 0, -- Average over 20 games
        form_rating REAL DEFAULT 0,             -- Based on last 5 games
        
        -- Tracking
        matches_counted INTEGER DEFAULT 0,      -- How many matches in the average (up to 20)
        form_trend TEXT,                        -- JSON: increasing/decreasing/stable
        
        -- Metadata
        last_updated TEXT,
        
        PRIMARY KEY (player_id, match_id)
    )''')
    
    # Create indices for common queries
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_player_stats_time 
                     ON player_running_stats(player_id, start_time)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_player_stats_team 
                     ON player_running_stats(team_id, start_time)''')
    
    # Create simplified player_squad_status table
    cursor.execute('''CREATE TABLE IF NOT EXISTS player_squad_status (
        player_id TEXT,
        team_id TEXT,
        player_name TEXT,
        last_appearance TEXT,
        is_in_squad BOOLEAN DEFAULT FALSE,
        PRIMARY KEY (player_id, team_id)
    )''')
    
    conn.commit()
    print("Player databases initialized successfully")

def calculate_player_match_importance(player_stats):
    """
    Calculate position-specific match importance score (0-35)
    Returns None if insufficient data (>50% None values)
    """
    
    # Check if we have enough valid data
    relevant_stats = [
        # Basic
        'minutes_played',
        
        # Goalkeeper specific
        'diving_saves',
        'penalties_saved',
        'shots_faced_saved',
        'shots_faced_total',
        'goals_conceded',
        'penalties_faced',
        
        # Distribution/Passing (both GK and outfield)
        'passes_total',
        'passes_successful',
        'long_passes_successful',
        
        # Goal Contributions (outfield)
        'goals_scored',
        'assists',
        'chances_created',
        
        # Defensive Actions
        'tackles_successful',
        'clearances',
        'interceptions',
        'defensive_blocks',
        
        # Ball Control
        'dribbles_completed',
        'crosses_successful',
        
        # Negative Actions
        'yellow_cards',
        'red_cards',
        'loss_of_possession',
        'fouls_committed',
        
        # New for position-specific scoring
        'shots_on_target'
    ]
    
    # If more than 50% of stats are None, return None for match importance...
    none_count = sum(1 for stat in relevant_stats if player_stats.get(stat) is None)
    if none_count / len(relevant_stats) > 0.5:  # More than 50% are None
        return None
        
    # If player didn't play, return None
    if player_stats.get('minutes_played', 0) == 0:
        return None
    
    # Default all stats to 0 if None
    stats = {k: (v if v is not None else 0) for k, v in player_stats.items()}
    
    score = 0
    minutes_weight = min(1.0, stats.get('minutes_played', 0) / 90)
    position = player_stats.get('position', 'unknown').lower()
    
    if position == 'goalkeeper':
        # Goalkeeper scoring (reduce further)
        # 1. Shot Stopping (max 20 points, down from 25)
        save_rate = 0
        if stats.get('shots_faced_total', 0) > 0:
            save_rate = (stats.get('shots_faced_saved', 0) / stats.get('shots_faced_total', 1)) * 100
        
        shot_stopping_score = (
            (stats.get('diving_saves', 0) * 1.5) +     # Down from 2
            (save_rate * 0.12) +                       # Down from 0.14
            (stats.get('penalties_saved', 0) * 4)      # Down from 5.5
        )
        score += min(20, shot_stopping_score)          # Down from 25
        
        # 2. Clean Sheet Bonus (max 10 points, down from 14)
        if stats.get('goals_conceded', 0) == 0:
            score += 10                                # Down from 14
        elif stats.get('goals_conceded', 0) == 1:
            score += 5                                 # Down from 7
        
        # 3. Distribution (max 10 points, down from 14)
        pass_accuracy = 0
        if stats.get('passes_total', 0) > 0:
            pass_accuracy = (stats.get('passes_successful', 0) / stats.get('passes_total', 1)) * 100
        
        distribution_score = (
            (pass_accuracy * 0.08) +                   # Down from 0.1
            (min(stats.get('long_passes_successful', 0) * 0.3, 3))  # Down from 0.35
        )
        score += min(10, distribution_score)           # Down from 14
        
    elif position == 'forward':
        # Attacking Contributions (75% - max 26 points, up from 24.5)
        attack_score = (
            (stats.get('goals_scored', 0) * 14) +     # Up from 12
            (stats.get('assists', 0) * 10) +          # Up from 8
            (stats.get('chances_created', 0) * 4) +   # Up from 3
            (stats.get('shots_on_target', 0) * 2.5) + # Up from 2
            (stats.get('dribbles_completed', 0) * 2)  # Up from 1.5
        )
        score += min(26, attack_score)
        
        # Secondary Contributions (30% - max 10.5 points)
        if stats.get('passes_total', 0) > 0:
            pass_accuracy = (stats.get('passes_successful', 0) / stats.get('passes_total', 1)) * 100
            secondary_score = (
                (pass_accuracy * 0.05) +                  # Up to 5 points for passing
                (stats.get('tackles_successful', 0) * 0.5) + # 0.5 points per tackle
                (stats.get('interceptions', 0) * 0.5)     # 0.5 points per interception
            )
            score += min(10.5, secondary_score)
            
    elif position == 'midfielder':
        # Playmaking (45% - max 16 points, up from 14)
        if stats.get('passes_total', 0) > 0:
            pass_accuracy = (stats.get('passes_successful', 0) / stats.get('passes_total', 1)) * 100
            playmaking_score = (
                (stats.get('assists', 0) * 10) +          # Up from 8
                (stats.get('chances_created', 0) * 4) +   # Up from 3
                (pass_accuracy * 0.1) +                   # Up from 0.08
                (stats.get('long_passes_successful', 0) * 0.8)  # Up from 0.5
            )
            score += min(16, playmaking_score)
        
        # Box-to-Box (45% - max 16 points, up from 14)
        box_score = (
            (stats.get('goals_scored', 0) * 10) +     # Up from 8
            (stats.get('tackles_successful', 0) * 2) + 
            (stats.get('interceptions', 0) * 2) +
            (stats.get('defensive_blocks', 0) * 2)     # Up from 1.5
        )
        score += min(16, box_score)
        
        # Ball Control (20% - max 7 points)
        control_score = (
            (stats.get('dribbles_completed', 0) * 2) +   # 2 points per dribble
            (min(stats.get('crosses_successful', 0) * 2, 6)) # Up to 6 points for crosses
        )
        score += min(7, control_score)
        
    elif position == 'defender':
        # Defensive Actions (60% - max 21 points, down from 24.5)
        defense_score = (
            (stats.get('tackles_successful', 0) * 2.5) +   # Down from 3
            (stats.get('clearances', 0) * 1.5) +          # Down from 2
            (stats.get('interceptions', 0) * 2) +         # Down from 2.5
            (stats.get('defensive_blocks', 0) * 2)        # Down from 2.5
        )
        # Clean sheet bonus reduced
        if stats.get('goals_conceded', 0) == 0:
            defense_score += 8                            # Down from 10
        elif stats.get('goals_conceded', 0) == 1:
            defense_score += 4                            # Down from 5
        score += min(21, defense_score)
        
        # Build-up Play (30% - max 10.5 points)
        if stats.get('passes_total', 0) > 0:
            pass_accuracy = (stats.get('passes_successful', 0) / stats.get('passes_total', 1)) * 100
            buildup_score = (
                (pass_accuracy * 0.06) +                 # Up to 6 points for passing
                (stats.get('long_passes_successful', 0) * 0.8) + # 0.8 points per long pass
                (stats.get('goals_scored', 0) * 5)       # 5 bonus points per goal
            )
            score += min(10.5, buildup_score)
    
    # Position-specific negative actions
    negative_score = 0
    if position == 'defender':
        negative_score = (
            (stats.get('loss_of_possession', 0) * -2) +  # More punishing for defenders
            (stats.get('fouls_committed', 0) * -3)       # More punishing for defenders
        )
    elif position == 'forward':
        negative_score = (
            (stats.get('loss_of_possession', 0) * -0.5) + # Less punishing for forwards
            (stats.get('fouls_committed', 0) * -1)        # Less punishing for forwards
        )
    else:  # midfielder and others
        negative_score = (
            (stats.get('loss_of_possession', 0) * -1) +
            (stats.get('fouls_committed', 0) * -2)
        )
    
    # Common negative actions
    negative_score += (
        (stats.get('yellow_cards', 0) * -5) +
        (stats.get('red_cards', 0) * -15)
    )
    
    score += negative_score
    
    # Apply minutes played weight and cap at 35
    final_score = score * minutes_weight
    return min(35, max(0, final_score))

def update_player_running_stats(conn, player_stats):
    """Update running stats for a player with detailed timing"""
    cursor = conn.cursor()
    
    try:
        # Get recent scores
        cursor.execute("""
            SELECT match_importance_score 
            FROM player_running_stats 
            WHERE player_id = ?
            AND match_importance_score IS NOT NULL
            ORDER BY start_time DESC 
            LIMIT 20
        """, (player_stats['player_id'],))
        recent_scores = [row[0] for row in cursor.fetchall()]

        # Calculate importance and form
        match_importance = calculate_player_match_importance(player_stats)
        
        # Overall importance - average of all recent scores
        if recent_scores:
            overall_importance = sum(recent_scores) / len(recent_scores)
        else:
            overall_importance = 0
        
        # Form rating - average of last 5 matches or all matches if less than 5
        if recent_scores:
            if len(recent_scores) >= 5:
                form_rating = sum(recent_scores[:5]) / 5  # Last 5 matches
            else:
                form_rating = sum(recent_scores) / len(recent_scores)  # All available matches
        else:
            form_rating = 0

        trend = calculate_trend(recent_scores)

        # Insert new record with position
        cursor.execute("""
            INSERT INTO player_running_stats (
                player_id, player_name, team_id, position, start_time, match_id,
                match_importance_score, overall_importance_score,
                form_rating, matches_counted, form_trend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player_stats['player_id'],
            player_stats['player_name'],
            player_stats['team_id'],
            player_stats.get('position', 'unknown'),  # Add position from player_stats
            player_stats['start_time'],
            player_stats['match_id'],
            match_importance,
            overall_importance,
            form_rating,
            len(recent_scores),
            trend
        ))

    except Exception as error:
        print(f"Error updating player {player_stats.get('player_name', 'unknown')}: {str(error)}")
        raise

def process_match_stats(conn, fixture_id, home_team_id, away_team_id, start_time, home_team_name, away_team_name):
    """
    Process all players' stats for a match and update their running stats
    Returns processed count and key player information
    """
    # Process all players first
    player_stats_list = get_match_player_stats(conn, fixture_id)
    
    if not player_stats_list:
        raise ValueError(f"No player stats found for match_id: {fixture_id}")
    
    # Update running stats for each player
    processed_count = 0
    errors = []
    
    for i, player_stats in enumerate(player_stats_list):
        try:
            update_player_running_stats(conn, player_stats)
            processed_count += 1
        except Exception as error:
            errors.append(f"Error processing player {player_stats.get('player_name', 'unknown')}: {str(error)}")
    
    
    if processed_count == 0:
        raise ValueError(f"Failed to process any players for match_id: {fixture_id}")
    

    # Get key players info
    home_count, home_key_players = get_key_players_count(conn, home_team_id, start_time)
    away_count, away_key_players = get_key_players_count(conn, away_team_id, start_time)

    # Get missing key players for both teams using passed parameters
    home_missing = get_missing_key_players(conn, fixture_id, home_team_id, start_time)
    away_missing = get_missing_key_players(conn, fixture_id, away_team_id, start_time)
    
    # Get strengths as dictionaries
    home_strengths = calculate_squad_strength(home_key_players, home_missing)
    away_strengths = calculate_squad_strength(away_key_players, away_missing)
    
    # Extract values from dictionaries
    home_team_gk_strength = home_strengths['goalkeeper_strength']
    home_team_defence_strength = home_strengths['defence_strength']
    home_team_midfield_strength = home_strengths['midfield_strength']
    home_team_attack_strength = home_strengths['attack_strength']
    home_team_overall_strength = home_strengths['overall_strength']
    
    away_team_gk_strength = away_strengths['goalkeeper_strength']
    away_team_defence_strength = away_strengths['defence_strength']
    away_team_midfield_strength = away_strengths['midfield_strength']
    away_team_attack_strength = away_strengths['attack_strength']
    away_team_overall_strength = away_strengths['overall_strength']

    
    print(f"\nKey players for {home_team_name}:")
    for player in home_key_players:
        print(f"  - {player['player_name']}: Importance={player['importance']}, Form={player['form']}, Average Score={player['average_score']}")
    
    print("Home key players missing:")
    for player in home_missing:
        print(f"  - {player['player_name']}: Importance={player['importance_score']}, Form={player['form_rating']}, Average Score={player['average_score']}")

    print("Home Team Strength: ", home_team_overall_strength)
    
    print(f"\nKey players for {away_team_name}:")
    for player in away_key_players:
        print(f"  - {player['player_name']}: Importance={player['importance']}, Form={player['form']}, Average Score={player['average_score']}")

    print("Away key players missing:")
    for player in away_missing:
        print(f"  - {player['player_name']}: Importance={player['importance_score']}, Form={player['form_rating']}, Average Score={player['average_score']}")
    
    print("Away Team Strength: ", away_team_overall_strength)
    
    return {
        'processed_count': processed_count,
        'home_team_id': home_team_id,
        'away_team_id': away_team_id,
        'home_key_players': home_key_players,
        'away_key_players': away_key_players,
        'home_key_players_missing': home_missing,
        'away_key_players_missing': away_missing,
        'home_team_gk_strength': home_team_gk_strength,
        'home_team_defence_strength': home_team_defence_strength,
        'home_team_midfield_strength': home_team_midfield_strength,
        'home_team_attack_strength': home_team_attack_strength,
        'home_team_overall_strength': home_team_overall_strength,
        'away_team_gk_strength': away_team_gk_strength,
        'away_team_defence_strength': away_team_defence_strength,
        'away_team_midfield_strength': away_team_midfield_strength,
        'away_team_attack_strength': away_team_attack_strength,
        'away_team_overall_strength': away_team_overall_strength,
    }

#Helper functions
#TODO: Simplify both of these functions to do it in one check, get all key players, are they missing?
def get_missing_key_players(conn, match_id, team_id, start_time):
    """Get key players (top 40%) who didn't play in this match"""
    cursor = conn.cursor()
    
    cursor.execute("""
        WITH player_rankings AS (
            SELECT 
                prs.player_id,
                prs.player_name,
                prs.position,
                prs.overall_importance_score,
                prs.form_rating,
                (prs.overall_importance_score * 0.4 + prs.form_rating * 0.6) as average_score,
                prs.start_time,
                ROW_NUMBER() OVER (
                    PARTITION BY prs.player_id 
                    ORDER BY prs.start_time DESC
                ) as recency_rank,
                NTILE(10) OVER (
                    PARTITION BY prs.team_id 
                    ORDER BY (prs.overall_importance_score * 0.4 + prs.form_rating * 0.6) DESC
                ) as percentile
            FROM player_running_stats prs
            WHERE prs.team_id = ?
            AND datetime(prs.start_time) >= datetime(?, '-30 days')
        )
        SELECT 
            player_id,
            player_name,
            position,
            overall_importance_score,
            form_rating,
            average_score
        FROM player_rankings
        WHERE recency_rank = 1
        AND percentile <= 4  -- Top 40% (4 out of 10 tiles)
        AND player_id NOT IN (
            SELECT player_id 
            FROM player_running_stats 
            WHERE match_id = ? 
            AND team_id = ?
        )
        ORDER BY average_score DESC
    """, (team_id, start_time, match_id, team_id))
    
    return [
        {
            'player_id': row[0],
            'player_name': row[1],
            'position': row[2],
            'importance_score': row[3],
            'form_rating': row[4],
            'average_score': row[5]
        }
        for row in cursor.fetchall()
    ]

def get_key_players_count(conn, team_id, start_time):
    """Get count and details of key players for a team (top 40% by performance)"""
    cursor = conn.cursor()
    cursor.execute("""
        WITH player_rankings AS (
            SELECT 
                prs.player_id,
                prs.player_name,
                prs.position,
                prs.overall_importance_score,
                prs.form_rating,
                (prs.overall_importance_score * 0.4 + prs.form_rating * 0.6) as average_score,
                ROW_NUMBER() OVER (
                    PARTITION BY prs.player_id 
                    ORDER BY prs.start_time DESC
                ) as recency_rank,
                NTILE(10) OVER (
                    PARTITION BY prs.team_id 
                    ORDER BY (prs.overall_importance_score * 0.4 + prs.form_rating * 0.6) DESC
                ) as percentile
            FROM player_running_stats prs
            WHERE team_id = ?
            AND datetime(prs.start_time) >= datetime(?, '-30 days')
        )
        SELECT 
            player_id,
            player_name,
            position,
            overall_importance_score as importance,
            form_rating as form,
            average_score
        FROM player_rankings
        WHERE recency_rank = 1
        AND percentile <= 4  -- Top 40% (4 out of 10 tiles)
        ORDER BY average_score DESC
    """, (team_id, start_time))
    
    players = [
        {
            'player_id': row[0],
            'player_name': row[1],
            'position': row[2],
            'importance': row[3],
            'form': row[4],
            'average_score': row[5]
        }
        for row in cursor.fetchall()
    ]
    
    return len(players), players

def calculate_trend(scores):
    """
    Calculate trend based on available scores (up to 5 matches)
    Returns: 'increasing', 'decreasing', or 'stable'
    """
    if len(scores) <= 1:
        return 'stable'
    
    # Use up to 5 most recent scores
    recent_five = scores[:5]
    
    # Calculate differences between consecutive matches
    differences = [recent_five[i] - recent_five[i+1] for i in range(len(recent_five)-1)]
    
    # Count positive and negative differences
    positives = sum(1 for d in differences if d > 0)
    negatives = sum(1 for d in differences if d < 0)
    
    # Calculate trend based on majority direction
    if len(differences) >= 2:  # Need at least 3 matches for meaningful trend
        if positives > len(differences) / 2:
            return 'increasing'
        elif negatives > len(differences) / 2:
            return 'decreasing'
    
    # If no clear trend or not enough matches
    return 'stable'

def get_match_player_stats(conn, match_id):
    """
    Get all player stats for a specific match
    
    Args:
        conn: Database connection
        match_id: ID of the match
    
    Returns:
        list: List of dictionaries containing each player's stats
    """
    cursor = conn.cursor()
    
    try:
        # Get all players' stats for this match
        cursor.execute("""
            SELECT *
            FROM player_stats 
            WHERE match_id = ?
        """, (match_id,))
        
        # Get column names
        columns = [description[0] for description in cursor.description]
        
        # Convert rows to list of dictionaries
        player_stats = []
        for row in cursor.fetchall():
            player_dict = dict(zip(columns, row))
            player_stats.append(player_dict)
            
        return player_stats
        
    except Exception as e:
        print(f"Error getting player stats for match {match_id}: {str(e)}")
        raise

def calculate_squad_strength(all_key_players, missing_players):
    """Calculate position-specific squad strengths with debug output"""
    print("\n=== Squad Strength Calculation Debug ===")
    
    # Debug: Print all key players and their positions
    print("\nAll Key Players:")
    for player in all_key_players:
        print(f"Name: {player.get('player_name', 'Unknown'):<20} "
              f"Position: {player.get('position', 'unknown'):<10} "
              f"Score: {player.get('average_score', 0):.2f}")
    
    # Debug: Print missing players
    print("\nMissing Players:")
    for player in missing_players:
        print(f"Name: {player.get('player_name', 'Unknown'):<20} "
              f"Position: {player.get('position', 'unknown'):<10} "
              f"Score: {player.get('average_score', 0):.2f}")
    
    if not all_key_players:
        print("\nNo key players found!")
        return {
            'goalkeeper_strength': None,
            'defence_strength': None,
            'midfield_strength': None,
            'attack_strength': None,
            'overall_strength': None
        }
    
    # Create a set of missing player IDs for quick lookup
    missing_ids = {p['player_id'] for p in missing_players}
    
    # Initialize position-specific strengths
    positions = {
        'goalkeeper': {'max': 0, 'actual': 0, 'weight': 1.0},
        'defender': {'max': 0, 'actual': 0, 'weight': 0.25},
        'midfielder': {'max': 0, 'actual': 0, 'weight': 0.33},
        'forward': {'max': 0, 'actual': 0, 'weight': 0.5},
        'unknown': {'max': 0, 'actual': 0, 'weight': 0.3}
    }
    
    # Calculate strengths by position
    print("\nPosition Calculations:")
    for i, player in enumerate(all_key_players):
        position = player.get('position', 'unknown').lower()
        ranking_weight = 1 / (i + 1)
        player_weight = ranking_weight * player['average_score']
        
        # Add to position totals
        if position in positions:
            position_weight = positions[position]['weight']
            weighted_score = position_weight * player_weight
            positions[position]['max'] += weighted_score
            if player['player_id'] not in missing_ids:
                positions[position]['actual'] += weighted_score
                print(f"Position: {position:<10} Player: {player['player_name']:<20} "
                      f"Weight: {weighted_score:.2f}")
    
    # Calculate strength ratios including unknown
    strengths = {
        'goalkeeper_strength': (
            positions['goalkeeper']['actual'] / positions['goalkeeper']['max'] 
            if positions['goalkeeper']['max'] > 0 else 1.0
        ),
        'defence_strength': (
            positions['defender']['actual'] / positions['defender']['max']
            if positions['defender']['max'] > 0 else 1.0
        ),
        'midfield_strength': (
            positions['midfielder']['actual'] / positions['midfielder']['max']
            if positions['midfielder']['max'] > 0 else 1.0
        ),
        'attack_strength': (
            positions['forward']['actual'] / positions['forward']['max']
            if positions['forward']['max'] > 0 else 1.0
        ),
        'unknown_strength': (  # Add unknown strength calculation
            positions['unknown']['actual'] / positions['unknown']['max']
            if positions['unknown']['max'] > 0 else 1.0
        )
    }
    
    # Calculate overall strength including unknown positions
    total_weight = 0
    weighted_strength = 0
    position_weights = {
        'goalkeeper_strength': 1.0,
        'defence_strength': 0.8,
        'midfield_strength': 0.6,
        'attack_strength': 0.7,
        'unknown_strength': 0.5  # Add weight for unknown positions
    }
    
    for pos, weight in position_weights.items():
        if strengths[pos] is not None:
            weighted_strength += strengths[pos] * weight
            total_weight += weight
            print(f"Adding {pos}: {strengths[pos]:.3f} * {weight} = {strengths[pos] * weight:.3f}")
    
    strengths['overall_strength'] = (
        weighted_strength / total_weight if total_weight > 0 else None
    )
    
    # Debug: Print final strengths
    print("\nFinal Strength Values:")
    for pos, strength in strengths.items():
        print(f"{pos:<20}: {strength:.3f}")
    
    print(f"Overall Strength: {strengths['overall_strength']:.3f}")
    print("=====================================\n")
    
    return strengths
