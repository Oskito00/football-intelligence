#TODO: Implement a simpler form feature extractor, the last one had too many features
# Was incredibly slow to train and didn't add much value to the model.

#Proposed implementation:
# 1. Get the last N matches for each team
# 2. Calculate the form for each team
# 3. Save the form to the form_history table

#Proposed features:
# 1. Form (Wins, Losses, Draws, Goals)
# 2. Form difference
# 3. Form trend
# 4. Form stability