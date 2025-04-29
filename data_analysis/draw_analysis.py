import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read CSV file
df = pd.read_csv('data/processed/matches.csv')  # Update filename as needed

# Filter columns
df = df[['home_score', 'away_score']]

# Create derived columns
df['total_goals'] = df['home_score'] + df['away_score']
df['is_draw'] = (df['home_score'] == df['away_score']).astype(int)

# Calculate draw percentages by total goals
draw_analysis = df.groupby('total_goals').agg(
    total_matches=('is_draw', 'count'),
    draw_percentage=('is_draw', 'mean')
).reset_index()

# Filter out total_goals with insufficient samples (optional)
draw_analysis = draw_analysis[draw_analysis['total_matches'] >= 10]

# Filter for even total goals
draw_analysis = draw_analysis[draw_analysis['total_goals'] % 2 == 0]

# Visualize
plt.figure(figsize=(10, 6))
sns.set_style("whitegrid")
ax = sns.lineplot(data=draw_analysis, x='total_goals', y='draw_percentage', 
                 marker='o', linewidth=2.5, markersize=8)

plt.title('Draw Probability for Even Total Goals', fontsize=14)
plt.xlabel('Total Goals in Match', fontsize=12)
plt.ylabel('Draw Probability', fontsize=12)
max_goals = int(draw_analysis['total_goals'].max())
plt.xticks(range(0, max_goals + 1, 2))  # Only even ticks
plt.ylim(0, 1)  # Full probability range

# Add data labels
for index, row in draw_analysis.iterrows():
    ax.text(row['total_goals'], row['draw_percentage']+0.01, 
           f"{row['draw_percentage']:.1%}\n(n={row['total_matches']})", 
           ha='center', fontsize=9)

plt.tight_layout()
plt.show()
