"""
Recent Form Analysis Function

Analyzes team performance in recent matches including win/draw/loss rates.
"""

import psycopg2
from typing import Dict, Any, Optional
from config import get_config


def get_recent_match_analysis(
    team_id: int,
    last_n_matches: int = 10,
    competition_id: Optional[str] = None,
    at_home: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Get recent match analysis for a team including win/draw/loss rates.
    
    Args:
        team_id: ID of the team to analyze
        last_n_matches: Number of recent matches to analyze (default: 10)
        competition_id: Optional competition ID to filter matches
        at_home: Optional filter for home/away matches (True=home, False=away, None=both)
    
    Returns:
        Dictionary containing analysis results
    """
    config = get_config()
    
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        
        # Build the query using UNION ALL for home and away matches
        query_parts = [
            """
            SELECT 
                m.match_id,
                m.start_time,
                m.home_team_name,
                m.away_team_name,
                m.result,
                m.competition_name,
                m.competition_id,
                'home' as team_side,
                m.result as team_result
            FROM matches m
            WHERE m.home_team_id = %s
            AND m.result IS NOT NULL
            """
        ]
        
        params = [team_id]
        
        # Add competition filter if specified
        if competition_id:
            query_parts[0] += " AND m.competition_id = %s"
            params.append(competition_id)
        
        # Add UNION ALL for away matches (unless filtering for home only)
        if at_home is None or not at_home:
            query_parts.append("""
            UNION ALL
            SELECT 
                m.match_id,
                m.start_time,
                m.home_team_name,
                m.away_team_name,
                m.result,
                m.competition_name,
                m.competition_id,
                'away' as team_side,
                CASE 
                    WHEN m.result = 'Home Win' THEN 'Away Win'
                    WHEN m.result = 'Away Win' THEN 'Home Win'
                    ELSE m.result
                END as team_result
            FROM matches m
            WHERE m.away_team_id = %s
            AND m.result IS NOT NULL
            """)
            params.append(team_id)
            
            # Add competition filter for away matches if specified
            if competition_id:
                query_parts[-1] += " AND m.competition_id = %s"
                params.append(competition_id)
        
        # Add ordering and limit
        query_parts.append("ORDER BY start_time DESC LIMIT %s")
        params.append(last_n_matches)
        
        query = " ".join(query_parts)
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        matches = cursor.fetchall()
        
        if not matches:
            return {
                "success": False,
                "error": f"No matches found for team ID {team_id}",
                "data": None
            }
        
        # Analyze the results
        total_matches = len(matches)
        wins = 0
        draws = 0
        losses = 0
        
        for match in matches:
            team_result = match[8]  # team_result column
            if team_result == 'Home Win' or team_result == 'Away Win':
                wins += 1
            elif team_result == 'Draw':
                draws += 1
            else:
                losses += 1
        
        # Calculate percentages
        win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0
        draw_rate = (draws / total_matches) * 100 if total_matches > 0 else 0
        loss_rate = (losses / total_matches) * 100 if total_matches > 0 else 0
        
        # Get team name from first match
        team_name = matches[0][2] if matches[0][7] == 'home' else matches[0][3]
        
        # Get competition info if filtered
        competition_info = None
        if competition_id and matches:
            competition_info = {
                "competition_id": matches[0][6],
                "competition_name": matches[0][5]
            }
        
        # Get home/away breakdown
        home_matches = [m for m in matches if m[7] == 'home']
        away_matches = [m for m in matches if m[7] == 'away']
        
        home_wins = sum(1 for m in home_matches if m[8] in ['Home Win', 'Away Win'])
        away_wins = sum(1 for m in away_matches if m[8] in ['Home Win', 'Away Win'])
        
        home_win_rate = (home_wins / len(home_matches) * 100) if home_matches else 0
        away_win_rate = (away_wins / len(away_matches) * 100) if away_matches else 0
        
        result = {
            "success": True,
            "error": None,
            "data": {
                "team_id": team_id,
                "team_name": team_name,
                "analysis_period": f"Last {total_matches} matches",
                "total_matches": total_matches,
                "overall_stats": {
                    "wins": wins,
                    "draws": draws,
                    "losses": losses,
                    "win_rate": round(win_rate, 1),
                    "draw_rate": round(draw_rate, 1),
                    "loss_rate": round(loss_rate, 1)
                },
                "home_away_breakdown": {
                    "home_matches": len(home_matches),
                    "away_matches": len(away_matches),
                    "home_win_rate": round(home_win_rate, 1),
                    "away_win_rate": round(away_win_rate, 1)
                },
                "competition_info": competition_info,
                "filters_applied": {
                    "last_n_matches": last_n_matches,
                    "competition_id": competition_id,
                    "at_home": at_home
                },
                "recent_matches": [
                    {
                        "match_id": match[0],
                        "date": match[1].strftime("%Y-%m-%d") if match[1] else None,
                        "home_team": match[2],
                        "away_team": match[3],
                        "result": match[4],
                        "team_side": match[7],
                        "team_result": match[8]
                    }
                    for match in matches[:5]  # Show last 5 matches
                ]
            }
        }
        
        cursor.close()
        conn.close()
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Database error: {str(e)}",
            "data": None
        }