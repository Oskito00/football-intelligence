def combine_stats(match_id, home_stats, away_stats):
    # Ensure match_id is first
    combined = {'match_id': match_id}
    
    # Add home stats
    combined.update(
        {f'home_{k}': v for k, v in home_stats.items()}
    )
    
    # Add away stats
    combined.update(
        {f'away_{k}': v for k, v in away_stats.items()}
    )
    
    return combined