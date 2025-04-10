import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd

# Initialize Dash app
app = dash.Dash(__name__)

# Load data
df = pd.read_csv('Data_Analysis/results/season_analysis.csv')

# Get valid seasons (excluding "All Seasons")
valid_seasons = df[df['Season'] != 'All Seasons']['Season']
years = valid_seasons.str[:4].astype(int)

# Create app layout
app.layout = html.Div([
    html.H1("Football Match Results Analysis Dashboard"),
    
    html.Div([
        dcc.Dropdown(
            id='category-selector',
            options=[
                {'label': 'By Competition', 'value': 'Competition'},
                {'label': 'By Country', 'value': 'Country'},
                {'label': 'By Season', 'value': 'Season'}
            ],
            value='Competition',
            style={'width': '50%'}
        ),
        dcc.Dropdown(
            id='metric-selector',
            options=[
                {'label': 'Draw Percentage', 'value': 'Draw %'},
                {'label': 'Home Win %', 'value': 'Home Win %'},
                {'label': 'Away Win %', 'value': 'Away Win %'}
            ],
            value='Draw %',
            style={'width': '50%'}
        )
    ], style={'padding': 20}),
    
    dcc.Graph(id='main-plot'),
    
    html.Div([
        dcc.RangeSlider(
            id='season-slider',
            min=years.min(),
            max=years.max(),
            value=[years.min(), years.max()],
            marks={str(year): str(year) for year in years.unique()},
            step=1
        )
    ], style={'padding': 40}),
    
    html.Div(id='data-table', style={'padding': 20})
])

@app.callback(
    [Output('main-plot', 'figure'),
     Output('data-table', 'children')],
    [Input('category-selector', 'value'),
     Input('metric-selector', 'value'),
     Input('season-slider', 'value')]
)
def update_dashboard(selected_category, selected_metric, selected_years):
    # Filter data, excluding "All Seasons" row
    filtered_df = df[df['Season'] != 'All Seasons'].copy()
    
    # Apply season filter
    filtered_df = filtered_df[
        filtered_df['Season'].str[:4].astype(int).between(selected_years[0], selected_years[1])
    ]
    
    # Calculate metrics if not present
    if 'Home Win %' not in filtered_df.columns:
        filtered_df['Home Win %'] = filtered_df['Home Wins'] / filtered_df['Total Matches']
        filtered_df['Away Win %'] = filtered_df['Away Wins'] / filtered_df['Total Matches']
    
    # Create plot
    fig = px.scatter(
        filtered_df,
        x=selected_category,
        y=selected_metric,
        color='Country',
        size='Total Matches',
        hover_data=['Competition', 'Season', 'Total Matches'],
        title=f"{selected_metric} {selected_category} Analysis",
        height=600
    )
    
    # Create data table
    table = dash.dash_table.DataTable(
        data=filtered_df.to_dict('records'),
        columns=[{'name': i, 'id': i} for i in filtered_df.columns],
        page_size=10,
        style_table={'overflowX': 'auto'}
    )
    
    return fig, table

if __name__ == '__main__':
    app.run(debug=True, port=8050) 