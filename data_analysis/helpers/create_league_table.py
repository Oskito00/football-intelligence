import pandas as pd
from collections import defaultdict

def generate_competition_tables(predictions_file):
    """Generate a league table based on predicted match results
    Used to evaluate the model and for some cool visualisations
    
    Args:
        predictions_file (str): The path to the predictions file
    
    Returns:
        pd.DataFrame: The league table
    """
    df = pd.read_csv(predictions_file)
    
    # Group by competition
    competitions = df['competition_name'].unique()

    
    all_tables = {}
    for competition in competitions:
        # Filter for this competition
        comp_df = df[df['competition_name'] == competition]
        
        # Calculate league table for just this competition's matches
        table = defaultdict(lambda: {
            'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'points': 0
        })
        
        # Process each match
        for _, match in comp_df.iterrows():
            home_team = match['home_team_name']
            away_team = match['away_team_name']
            result = match['predicted_result']
            
            # Update games played
            table[home_team]['played'] += 1
            table[away_team]['played'] += 1
            
            if result == 0:
                table[home_team]['won'] += 1
                table[home_team]['points'] += 3
                table[away_team]['lost'] += 1
            elif result == 2:
                table[away_team]['won'] += 1
                table[away_team]['points'] += 3
                table[home_team]['lost'] += 1
            else:  # draw
                table[home_team]['drawn'] += 1
                table[away_team]['drawn'] += 1
                table[home_team]['points'] += 1
                table[away_team]['points'] += 1
        
        # Convert to DataFrame
        table_df = pd.DataFrame.from_dict(table, orient='index').reset_index()
        table_df = table_df.rename(columns={'index': 'team'})
        
        # Sort by points
        table_df = table_df.sort_values(by=['points'], ascending=[False])
        
        # Add position column
        table_df.insert(0, 'position', range(1, len(table_df) + 1))
        
        all_tables[competition] = table_df
    
    return all_tables

if __name__ == "__main__":
    # File path
    predictions_file = "machine_learning/predictions/XGBOOST/predictions/predictions_78_2022.csv"

    year = predictions_file.split('_')[-1].split('.')[0]
    
    # Generate tables
    tables = generate_competition_tables(predictions_file)
    
    # Print tables
    for competition, table in tables.items():
        print(f"\n{competition} - Predicted Final Table")
        print("=" * 80)
        print(table[['position', 'team', 'played', 'won', 'drawn', 'lost', 'points']])
        
        # Save to CSV
        output_file = f"machine_learning/predictions/XGBOOST/league_tables/predicted_table_{competition.replace(' ', '_')}_{year}.csv"
        table.to_csv(output_file, index=False)
        print(f"Table saved to {output_file}")