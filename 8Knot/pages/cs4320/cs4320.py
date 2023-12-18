from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

from .visualizations.cntrb_count import gc_cntrb_over_time
from .visualizations.issues_closed_over_time import gc_issues_closed_over_time
from .visualizations.commit_freq import gc_commit_freq
from .visualizations.top_repos_by_issue import gc_cumulative_issues_over_time
from .visualizations.pr_vis import gc_pr_closure_time_distribution


warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/cs4320")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_cntrb_over_time, width=6),
                dbc.Col(gc_issues_closed_over_time, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_commit_freq, width=6),
                dbc.Col(gc_cumulative_issues_over_time, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_pr_closure_time_distribution, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)
