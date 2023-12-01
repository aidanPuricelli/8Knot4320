from dash import html, dcc, callback
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.pr_assignee_query import pr_assignee_query as praq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import datetime as dt

PAGE = "cs4320"
VIZ_ID = "cntrb_over_time"

gc_cntrb_over_time = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Contributor Count Over Time",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Visualizes contributor count over time.
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
                                    "Total Assignments Required:",
                                    html_for=f"assignments-required-{PAGE}-{VIZ_ID}",
                                    width={"size": "auto"},
                                ),
                                dbc.Col(
                                    dbc.Input(
                                        id=f"assignments-required-{PAGE}-{VIZ_ID}",
                                        type="number",
                                        min=1,
                                        max=250,
                                        step=1,
                                        value=10,
                                        size="sm",
                                    ),
                                    className="me-2",
                                    width=1,
                                ),
                                dbc.Alert(
                                    children="No contributors meet assignment requirement",
                                    id=f"check-alert-{PAGE}-{VIZ_ID}",
                                    dismissable=True,
                                    fade=False,
                                    is_open=False,
                                    color="warning",
                                ),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-radio-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        dbc.RadioItems(
                                            id=f"date-radio-{PAGE}-{VIZ_ID}",
                                            options=[
                                                {"label": "Trend", "value": "D"},
                                                {"label": "Week", "value": "W"},
                                                {"label": "Month", "value": "M"},
                                                {"label": "Year", "value": "Y"},
                                            ],
                                            value="W",
                                            inline=True,
                                        ),
                                    ]
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
        )
    ],
)


# callback for pull request review assignment graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"),
    [
        Input("repo-choices", "data"),
        Input(f"date-radio-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def cntrib_pr_assignment_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=praq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=praq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph, False

    df = process_data(df, interval)

    fig = create_figure(df, interval)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig, False


def process_data(df: pd.DataFrame, interval):
    # Convert to datetime objects
    df['created'] = pd.to_datetime(df['created'], utc=True)

    # Order values chronologically
    df = df.sort_values(by='created')

    # Group by time interval and count unique contributors
    df_grouped = df.groupby(pd.Grouper(key='created', freq=interval))['assignee'].nunique().reset_index()
    df_grouped.rename(columns={'assignee': 'contributor_count'}, inplace=True)

    return df_grouped


def create_figure(df: pd.DataFrame, interval):
    # Create a line or bar chart based on the interval
    if interval in ['D', 'W']:
        fig = px.line(df, x='created', y='contributor_count', title='Contributor Count Over Time')
    else:
        fig = px.bar(df, x='created', y='contributor_count', title='Contributor Count Over Time')

    # Update layout and labels
    fig.update_layout(xaxis_title='Time', yaxis_title='Number of Contributors')
    return fig



def pr_assignment(df, start_date, end_date, contrib):
    """
    This function takes a start and an end date and determines how many
    prs that are open during that time interval and are currently assigned
    to the contributor.

    Args:
    -----
        df : Pandas Dataframe
            Dataframe with issue assignment actions of the assignees

        start_date : Datetime Timestamp
            Timestamp of the start time of the time interval

        end_date : Datetime Timestamp
            Timestamp of the end time of the time interval

        contrib : str
            contrb_id for the contributor

    Returns:
    --------
        int: Number of assignments to the contributor in the time window
    """

    # drop rows not by contrib
    df = df[df["assignee"] == contrib]

    # drop rows that are more recent than the end date
    df_created = df[df["created"] <= end_date]

    # Keep issues that were either still open after the 'start_date' or that have not been closed.
    df_in_range = df_created[(df_created["closed"] > start_date) | (df_created["closed"].isnull())]

    # get all issue unassignments and drop rows that have been unassigned more recent than the end date
    df_unassign = df_in_range[
        (df_in_range["assignment_action"] == "unassigned") & (df_in_range["assign_date"] <= end_date)
    ]

    # get all issue assignments and drop rows that have been assigned more recent than the end date
    df_assigned = df_in_range[
        (df_in_range["assignment_action"] == "assigned") & (df_in_range["assign_date"] <= end_date)
    ]

    # return the different of assignments and unassignments
    return df_assigned.shape[0] - df_unassign.shape[0]
