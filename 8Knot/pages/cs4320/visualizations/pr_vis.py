from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import numpy as np 
import datetime as dt
import logging
from pages.utils.graph_utils import get_graph_time_values, color_seq
import io
from pages.utils.job_utils import nodata_graph
from queries.prs_query import prs_query as prq
from cache_manager.cache_manager import CacheManager as cm
import time

PAGE = "cs4320"
VIZ_ID = "prs-closure-time-distribution"

gc_pr_closure_time_distribution = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Pull Request Closure Time Distribution",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Visualizes the distribution of the time it takes to close pull requests.
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },
                                            {"label": "Month", "value": "M"},
                                            {"label": "Year", "value": "Y"},
                                        ],
                                        value="M",
                                        inline=True,
                                    ),
                                    className="me-2",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        ),
    ],
)

# formatting for graph generation
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open

# callback for pull request closure time distribution graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def pr_closure_time_distribution_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=prq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=prq, repos=repolist)

    # data ready.
    start = time.perf_counter()
    logging.warning("PULL REQUEST CLOSURE TIME DISTRIBUTION - START")

    # test if there is data
    if df.empty:
        logging.warning("PULL REQUEST CLOSURE TIME DISTRIBUTION - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    closure_times, bin_edges = process_data(df, interval)

    fig = create_figure(closure_times, bin_edges, interval)  # Pass interval argument

    logging.warning(f"PULL REQUEST CLOSURE TIME DISTRIBUTION - END - {time.perf_counter() - start}")

    return fig


# Modify the process_data function to calculate closure times
# Modify the process_data function to calculate closure times and return bin edges
def process_data(df: pd.DataFrame, interval):
    # convert dates to datetime objects rather than strings
    df["created"] = pd.to_datetime(df["created"], utc=True)
    df["closed"] = pd.to_datetime(df["closed"], utc=True)

    # Calculate closure times for each pull request
    df["closure_time"] = (df["closed"] - df["created"]).dt.total_seconds() / 3600  # Convert to hours

    # Remove outliers (e.g., negative closure times)
    df = df[(df["closure_time"] >= 0) & (df["closure_time"] <= 1000)]  # Adjust the range as needed

    # Create bins for the histogram based on the interval
    if interval == "D":
        bins = 24  # 1 bin per hour
    elif interval == "W":
        bins = 7  # 1 bin per day
    elif interval == "M":
        bins = 30  # 1 bin per day (approximate)
    elif interval == "Y":
        bins = 365  # 1 bin per day (approximate)
    else:
        bins = 100  # Default to 100 bins

    # Create a histogram of closure times and return bin edges
    closure_times = df["closure_time"]
    histogram, bin_edges = np.histogram(closure_times, bins=bins)

    return histogram, bin_edges

# Modify the create_figure function to visualize the closure time distribution
def create_figure(closure_times, bin_edges, interval):
    # Generate bin labels for the x-axis
    bin_labels = []
    for i in range(len(bin_edges) - 1):
        bin_labels.append(f"{int(bin_edges[i])}-{int(bin_edges[i+1])}")

    # Create a bar chart to visualize the closure time distribution
    fig = go.Figure(data=[go.Bar(x=bin_labels, y=closure_times, text=closure_times, textposition='auto')])

    # Customize the layout
    fig.update_layout(
        xaxis_title="Closure Time (Hours)",
        yaxis_title="Frequency",
        title=f"Closure Time Distribution ({interval} Intervals)",
        font=dict(size=14),
    )

    return fig

