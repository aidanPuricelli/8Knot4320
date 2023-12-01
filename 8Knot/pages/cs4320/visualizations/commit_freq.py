from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import pandas as pd
import logging
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.commits_query import commits_query as cmq
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import io
import time

PAGE = "cs4320"
VIZ_ID = "commit-frequency"

gc_commit_freq = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Commit Frequency",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Visualizes commit frequency.
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",  # needs to be the same as dbc.Button id
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


# callback for commits over time graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [Input("repo-choices", "data")],
    background=True,
)
def commits_over_time_graph(repolist):
    # Start time recorded
    start = time.perf_counter()

    cache = cm()
    df = cache.grabm(func=cmq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=cmq, repos=repolist)

    # Check if DataFrame is empty
    if df.empty:
        logging.warning("COMMITS OVER TIME - NO DATA AVAILABLE")
        return nodata_graph

    # Rename 'date' column to 'created'
    if 'date' in df.columns:
        df.rename(columns={'date': 'created'}, inplace=True)

    # Continue with processing
    df_created = process_data(df)

    fig = create_figure(df_created)

    # Logging the end time and duration
    logging.warning(f"COMMITS_OVER_TIME_VIZ - END - {time.perf_counter() - start}")
    return fig



def process_data(df: pd.DataFrame):
    df["created"] = pd.to_datetime(df["created"], utc=True)

    # Group by week and count commits
    df_created = (
        df.groupby(pd.Grouper(key='created', freq='W-MON'))
        .size()
        .reset_index(name='commits')
    )

    # Ensure the date is at the start of the week
    df_created['Date'] = df_created['created'] - pd.to_timedelta(df_created['created'].dt.dayofweek, unit='d')

    return df_created



def create_figure(df_created: pd.DataFrame):
    fig = px.bar(
        df_created,
        x="Date",
        y="commits",
        labels={"Date": "Week", "commits": "Number of Commits"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_layout(
        xaxis_title="Week",
        yaxis_title="Number of Commits",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )
    fig.update_traces(hovertemplate="Week: %{x}<br>Commits: %{y}<br>")

    return fig

