"""
Analyze match result distributions across competitions and seasons.
"""

import sqlite3
import csv
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
from typing import List, Dict, DefaultDict

# Configuration
OUTPUT_DIR = 'Data_Analysis/results'
CSV_HEADER = [
    'Country', 'Competition', 'Competition ID', 'Season',
    'Home Wins', 'Draws', 'Away Wins', 'Total Matches', 'Draw %'
]
CATEGORIES = {
    'comp_name': "Competition",
    'country': "Country",
    'season_id': "Season"
}

@dataclass
class Match:
    """Represents a football match with key metadata."""
    comp_id: str
    comp_name: str
    country: str
    season_id: str
    season_start: str
    home_score: int
    away_score: int

    @property
    def result(self) -> str:
        """Determine match result as home_win/draw/away_win."""
        if self.home_score > self.away_score:
            return 'home_win'
        if self.home_score < self.away_score:
            return 'away_win'
        return 'draw'

def get_data(conn: sqlite3.Connection) -> List[Match]:
    """Retrieve matches data from database."""
    cursor = conn.cursor()
    query = """
        SELECT 
            competition_id, 
            competition_name, 
            competition_country, 
            competition_season_id, 
            season_start_date, 
            home_score, 
            away_score 
        FROM matches 
        WHERE home_score IS NOT NULL 
            AND away_score IS NOT NULL
    """
    cursor.execute(query)
    return [Match(*row) for row in cursor.fetchall()]

def calculate_distribution(matches: List[Match]) -> Dict[str, int]:
    """Calculate result distribution for a set of matches."""
    results = {
        'home_wins': 0,
        'draws': 0,
        'away_wins': 0,
        'total_matches': len(matches)
    }
    for match in matches:
        if match.result == 'home_win':
            results['home_wins'] += 1
        elif match.result == 'away_win':
            results['away_wins'] += 1
        else:
            results['draws'] += 1
    return results

def analyze_by_category(matches: List[Match], category: str) -> Dict[str, Dict]:
    """Analyze results distribution by a specified category."""
    category_results = defaultdict(lambda: {
        'home_wins': 0,
        'draws': 0,
        'away_wins': 0,
        'total_matches': 0
    })
    
    for match in matches:
        category_value = getattr(match, category)
        res = category_results[category_value]
        
        if match.result == 'home_win':
            res['home_wins'] += 1
        elif match.result == 'away_win':
            res['away_wins'] += 1
        else:
            res['draws'] += 1
        res['total_matches'] += 1
    
    return category_results

def get_season_label(match: Match) -> str:
    """Generate formatted season label from start date."""
    try:
        year = datetime.strptime(match.season_start, '%Y-%m-%d').year
        return f"{year}-{year+1}"
    except ValueError:
        return match.season_id

def analyze_seasons(matches: List[Match]) -> DefaultDict:
    """Analyze results by competition and season."""
    season_data = defaultdict(lambda: defaultdict(lambda: {
        'home_wins': 0,
        'draws': 0,
        'away_wins': 0,
        'total_matches': 0
    }))
    
    competition_metadata = {}  # {comp_key: (country, comp_name, comp_id)}

    for match in matches:
        comp_key = f"{match.comp_name} ({match.comp_id})"
        season_label = get_season_label(match)
        
        # Store competition metadata
        if comp_key not in competition_metadata:
            competition_metadata[comp_key] = (match.country, match.comp_name, match.comp_id)
        
        # Update counts
        res = season_data[comp_key][season_label]
        if match.result == 'home_win':
            res['home_wins'] += 1
        elif match.result == 'away_win':
            res['away_wins'] += 1
        else:
            res['draws'] += 1
        res['total_matches'] += 1

    # Prepare CSV data
    csv_rows = []
    for comp_key in sorted(season_data.keys()):
        country, comp_name, comp_id = competition_metadata[comp_key]
        for season in sorted(season_data[comp_key].keys()):
            res = season_data[comp_key][season]
            draw_pct = res['draws'] / res['total_matches'] if res['total_matches'] > 0 else 0
            csv_rows.append([
                country,
                comp_name,
                comp_id,
                season,
                res['home_wins'],
                res['draws'],
                res['away_wins'],
                res['total_matches'],
                round(draw_pct, 4)
            ])

    # Add summary row
    total_home = sum(row[4] for row in csv_rows)
    total_draws = sum(row[5] for row in csv_rows)
    total_away = sum(row[6] for row in csv_rows)
    total_matches = sum(row[7] for row in csv_rows)
    csv_rows.append([
        'All Countries', 'All Competitions', 'ALL', 'All Seasons',
        total_home, total_draws, total_away, total_matches,
        round(total_draws / total_matches, 4) if total_matches > 0 else 0
    ])

    # Save to CSV
    with open(f'{OUTPUT_DIR}/season_analysis.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(csv_rows)

    return season_data

def print_distribution(results: Dict, title: str) -> None:
    """Print formatted distribution results."""
    print(f"\n{title}")
    print("=" * 40)
    print(f"Total Matches: {results['total_matches']}")
    print(f"Home Wins: {results['home_wins']} ({results['home_wins']/results['total_matches']:.2%})")
    print(f"Draws: {results['draws']} ({results['draws']/results['total_matches']:.2%})")
    print(f"Away Wins: {results['away_wins']} ({results['away_wins']/results['total_matches']:.2%})")

def main():
    """Main analysis workflow."""
    conn = sqlite3.connect('v2db.sqlite')
    matches = get_data(conn)
    conn.close()

    # Overall distribution
    overall = calculate_distribution(matches)
    print_distribution(overall, "Overall Match Results Distribution")

    # Category analysis
    for category, label in CATEGORIES.items():
        results = analyze_by_category(matches, category)
        print(f"\n\n{'='*40}\nAnalysis by {label}\n{'='*40}")
        for value, stats in results.items():
            print_distribution(stats, f"{label}: {value}")

    # Season analysis
    season_analysis = analyze_seasons(matches)
    print("\n\n" + "="*40 + "\nSeason Analysis by Competition\n" + "="*40)
    for comp in season_analysis:
        print(f"\nCompetition: {comp}")
        for season in season_analysis[comp]:
            res = season_analysis[comp][season]
            print(f"  Season {season}:")
            print(f"    Home Wins: {res['home_wins']} ({res['home_wins']/res['total_matches']:.1%})")
            print(f"    Draws: {res['draws']} ({res['draws']/res['total_matches']:.1%})")
            print(f"    Away Wins: {res['away_wins']} ({res['away_wins']/res['total_matches']:.1%})")
            print(f"    Total Matches: {res['total_matches']}")

if __name__ == "__main__":
    main()



