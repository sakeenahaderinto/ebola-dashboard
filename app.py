import pandas as pd
import plotly.express as px
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

# Data Cleaning & Manipulation function
def clean_manip_data():
    df = pd.read_csv('assets/ebola_sierra_leone.csv')
    
    # Convert date columns with error handling
    df['date_of_onset'] = pd.to_datetime(df['date_of_onset'], errors='coerce')
    df['date_of_sample'] = pd.to_datetime(df['date_of_sample'], errors='coerce')
    
    # Filter valid dates
    df = df[df['date_of_sample'] >= df['date_of_onset']]
    
    # Age pre-processing
    df['age'] = df['age'].fillna(df['age'].median()).astype(int)
    df['age_group'] = pd.cut(df['age'], 
                            bins=[0, 18, 35, 60, 100], 
                            labels=['0-18', '19-35', '36-60', '61+']).astype('category')
    
    # Calculate time to sample
    df['time_to_sample'] = (df['date_of_sample'] - df['date_of_onset']).dt.days
    
    return df

# Load and clean data
df = clean_manip_data()

# Create filtered datasets
daily_cases = df.groupby(['date_of_onset', 'status']).size().reset_index(name='cases')
cumulative = daily_cases.sort_values('date_of_onset')
cumulative['cumulative_cases'] = cumulative.groupby('status')['cases'].cumsum()

# Metric calculation function
def calculate_metrics(filtered_df):
    total_confirmed = filtered_df[filtered_df['status'] == 'confirmed'].shape[0]
    avg_time_to_sample = filtered_df['time_to_sample'].mean()  
    status_ratio = filtered_df['status'].value_counts(normalize=True).get('confirmed', 0) * 100
    return total_confirmed, round(avg_time_to_sample, 1), round(status_ratio, 1)

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

# App layout
app.layout = dbc.Container(fluid=True, children=[
    # Header
    html.Div([
        dbc.Row([
            dbc.Col([html.H1("Ebola Outbreak Dashboard")], className='title-header')])
    ], className="dashboard-header"),
    
    # Filters Section
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Select Districts:", className="mb-2"),
                dcc.Dropdown(
                    id='district-filter',
                    options=[{'label': d, 'value': d} for d in sorted(df['district'].unique())],
                    multi=True,
                    value=df['district'].unique().tolist(),
                    placeholder="All Districts",
                    className='neu-input'
                )
            ], md=6),
            
            dbc.Col([
                html.Label("Filter Age Groups:", className="mb-2"),
                dbc.Checklist(
                    id='age-group-filter',
                    options=[{'label': grp, 'value': grp} for grp in df['age_group'].cat.categories],
                    value=df['age_group'].cat.categories.tolist(),
                    inline=True,
                    className='neu-input'
                )
            ], md=6)
        ])
    ], className="filter-section"),
    
    # Metrics Cards
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Total Confirmed Cases"),
            dbc.CardBody([
                html.H2(id='total-cases', className="card-title"),
                html.Small("📈 Trend from initial data", className="text-muted")
            ])
        ], className="metric-card"), md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Avg Time to Sample"),
            dbc.CardBody([
                html.H2(id='avg-time', className="card-title"),
                html.Small("⏳ Days from onset to sample", className="text-muted")
            ])
        ], className="metric-card"), md=4),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Confirmed Ratio"),
            dbc.CardBody([
                html.H2(id='status-ratio', className="card-title"),
                html.Small("✅ Confirmed vs Suspected", className="text-muted")
            ])
        ], className="metric-card"), md=4),
    ], className="mb-4 g-4"),
    
    # Main Visualizations(Time Series & Grouped Bar Chart)
    dbc.Row([
        dbc.Col(
            html.Div(
                dcc.Graph(id='district-plot'),
                className="dash-graph"
            ), md=6
        ),
        dbc.Col(
            html.Div(
                dcc.Graph(id='time-series-plot'),
                className="dash-graph"
            ), md=6
        )
    ], className="mb-4"),
    
    # Status Pie & Histogram Visualizations
    dbc.Row([
        dbc.Col(
            html.Div(
                dcc.Graph(id='age-histogram'),
                className="dash-graph"
            ), md=6
        ),
        dbc.Col(
            html.Div(
                dcc.Graph(id='status-pie'),
                className="dash-graph"
            ), md=6
        )
    ])
], className="app-container", id='main-container')



# Update metrics callback
@app.callback(
    [Output('total-cases', 'children'),
     Output('avg-time', 'children'),
     Output('status-ratio', 'children')],
    [Input('district-filter', 'value')]
)
def update_metrics(selected_districts):
    filtered_df = df[df['district'].isin(selected_districts)]
    total, avg, ratio = calculate_metrics(filtered_df)
    return f"{total:,}", f"{avg} days", f"{ratio}%"

# Update district plot callback
@app.callback(
    Output('district-plot', 'figure'),
    [Input('district-filter', 'value')]
)
def update_district_plot(selected_districts):
    filtered_df = df[df['district'].isin(selected_districts)]
    agg_df = filtered_df.groupby(['district', 'status']).size().reset_index(name='count')
    
    fig = px.bar(
        agg_df, 
        x='district', 
        y='count', 
        color='status', 
        barmode='group',
        title='Case Distribution by District',
        labels={'count': 'Number of Cases'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#2d4263'},
        xaxis_title="District",
        yaxis_title="Cases",
        hovermode="x unified"
    )

# Update time series callback
@app.callback(
    Output('time-series-plot', 'figure'),
    [Input('district-filter', 'value')]
)
def update_time_series(selected_districts):
    filtered = df[df['district'].isin(selected_districts)]
    time_series = filtered.groupby(['date_of_onset', 'status']).size().reset_index(name='count')
    
    fig = px.line(
        time_series,
        x='date_of_onset',
        y='count',
        color='status',
        title='Case Trend Over Time',
        labels={'count': 'Number of Cases', 'date_of_onset': 'Date'},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#2d4263'},
        xaxis_title="Date",
        yaxis_title="Daily Cases",
        hovermode="x unified"
    )

# Update histogram callback
@app.callback(
    Output('age-histogram', 'figure'),
    [Input('district-filter', 'value'),
     Input('age-group-filter', 'value')]
)
def update_histogram(selected_districts, selected_groups):
    filtered_df = df[
        (df['district'].isin(selected_districts)) &
        (df['age_group'].isin(selected_groups)) &
        (df['status'] == 'confirmed')
    ]
    
    fig = px.histogram(
        filtered_df,
        x='age_group',
        title='Confirmed Cases by Age Group',
        labels={'age_group': 'Age Group', 'count': 'Confirmed Cases'},
        color='age_group',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#2d4263'},
        xaxis_title="Age Group",
        yaxis_title="Cases",
        bargap=0.15,
        showlegend=False
    )

# Status pie chart callback
@app.callback(
    Output('status-pie', 'figure'),
    [Input('district-filter', 'value')]
)
def update_status_pie(selected_districts):
    filtered_df = df[df['district'].isin(selected_districts)]
    status_counts = filtered_df['status'].value_counts().reset_index()
    
    fig = px.pie(
        status_counts,
        names='status',
        values='count',
        title='Case Status Distribution',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    return fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': '#2d4263'}
    )

if __name__ == '__main__':
    app.run(debug=True, port=8056)