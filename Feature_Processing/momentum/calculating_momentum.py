# Suggested momentum calculation:
#   for match in [last 5 matches]:
#       momentum += 1 (win)
#       momentum -= 1 (loss)


def calculate_momentum(last_five_scores):

    momentum = 0;
    for score in last_five_scores:
        
        goals = score[0]
        opp_goals = score[1]

        if goals > opp_goals:
            momentum += 1
        elif goals < opp_goals:
            momentum -= 1
        else:
            continue

    return momentum;   


def last_five_scores(match_id, home_or_away):
    '''
    ONLY works given rows ordered by clean_date.
    '''
    


