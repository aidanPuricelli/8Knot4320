from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from pages.utils.graph_utils import get_graph_time_values, color_seq
from pages.utils.job_utils import nodata_graph
from queries.issues_query import issues_query as iq
from cache_manager.cache_manager import CacheManager as cm
import io
import time

PAGE = "cs4320"
VIZ_ID = "issues-closed-over-time"

gc_issues_closed_over_time = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Issues Closed Over Time",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Visualizes issues closed over time.
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


# callback for issues over time graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def issues_over_time_graph(repolist, interval):
    cache = cm()
    df = cache.grabm(func=iq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=iq, repos=repolist)

    start = time.perf_counter()
    logging.warning("ISSUES OVER TIME - START")

    if df.empty:
        logging.warning("ISSUES OVER TIME - NO DATA AVAILABLE")
        return nodata_graph

    df_closed = process_data(df, interval)

    fig = create_figure(df_closed, interval)

    logging.warning(f"ISSUES_OVER_TIME_VIZ - END - {time.perf_counter() - start}")

    return fig



def process_data(df: pd.DataFrame, interval):
    df["closed"] = pd.to_datetime(df["closed"], utc=True)
    df = df.sort_values(by="closed", axis=0, ascending=True)

    period_slice = None
    if interval == "W":
        period_slice = 10

    # DataFrame for closed issues in the time interval
    closed_range = pd.to_datetime(df["closed"]).dt.to_period(interval).value_counts().sort_index()
    df_closed = closed_range.to_frame().reset_index().rename(columns={"index": "Date", "closed": "Closed"})
    df_closed["Date"] = pd.to_datetime(df_closed["Date"].astype(str).str[:period_slice])

    # Formatting for graph generation
    if interval == "M":
        df_closed["Date"] = df_closed["Date"].dt.strftime("%Y-%m-01")
    elif interval == "Y":
        df_closed["Date"] = df_closed["Date"].dt.strftime("%Y-01-01")

    return df_closed



def create_figure(df_closed: pd.DataFrame, interval):
    x_r, x_name, hover, period = get_graph_time_values(interval)

    fig = go.Figure()
    fig.add_bar(
        x=df_closed["Date"],
        y=df_closed["Closed"],
        opacity=0.9,
        hovertemplate=hover + "<br>Closed: %{y}<br>" + "<extra></extra>",
        marker=dict(color=color_seq[4]),
        name="Closed",
    )

    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )

    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Number of Closed Issues",
        margin_b=40,
        font=dict(size=14),
    )

    return fig



# for each day, this function calculates the amount of open issues
def get_open(df, date):
    # drop rows that are more recent than the date limit
    df_lim = df[df["created"] <= date]

    # drops rows that have been closed after date
    df_open = df_lim[df_lim["closed"] > date]

    # include issues that have not been close yet
    df_open = pd.concat([df_open, df_lim[df_lim.closed.isnull()]])

    # generates number of columns ie open issues
    num_open = df_open.shape[0]
    return num_open
