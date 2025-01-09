from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash
import plotly.express as px

import pandas as pd

from datetime import date


from ...utilities.logic_ch3 import (
    get_names_of_seed_lists,
    get_seed_list_preview,
    get_seed_channel_metadata,
    get_birth_chart_data,
    get_time_series_chart_data,
    render_message_table,
    translate_messages,
)

layout = html.Div(
    [
        html.H1("Analysis page"),
        dcc.Dropdown(
            id="seed-list-menu",
            options=[],
            placeholder="Select your seed list(s)",
            style={"color": "black"},
            value=None,
            disabled=False,
            multi=True,
        ),
        html.Div(id="seed-list-menu-feedback"),
    ]
)


@dash.callback(Output("seed-list-menu", "options"), Input("seed-list-menu", "options"))
def populate_menu_with_seed_lists(my_options: list[dict]) -> list[dict]:
    # Query the database for all seed lists
    my_seed_lists = get_names_of_seed_lists()
    return [
        {"label": f"{my_seed_list}", "value": f"{my_seed_list}"}
        for my_seed_list in my_seed_lists
    ]


@dash.callback(
    Output("seed-list-menu-feedback", "children"), Input("seed-list-menu", "value")
)
def display_seed_list_preview_and_date_range_picker(my_seed_lists: list[str]) -> html:
    if not isinstance(my_seed_lists, list) or len(my_seed_lists) == 0:
        return None
    records = get_seed_list_preview(my_seed_lists)

    return html.Div(
        [
            dash_table.DataTable(
                data=records,
                columns=[{"name": key, "id": key} for key in records[0].keys()],
                style_cell={"textAlign": "left"},
                page_current=0,
                page_size=10,
                export_format="csv",
                sort_action="native",
            ),
            html.Div(
                [
                    dcc.DatePickerRange(
                        id="my-date-picker-range",
                        min_date_allowed=date(2013, 1, 1),
                        max_date_allowed=date(2099, 12, 31),
                        initial_visible_month=date.today(),
                        start_date=None,
                        end_date=None,
                        disabled=False,
                    ),
                    html.Div(id="my-date-picker-range-feedback"),
                ]
            ),
        ]
    )


@dash.callback(
    Output("my-date-picker-range-feedback", "children"),
    Input("my-date-picker-range", "start_date"),
    Input("my-date-picker-range", "end_date"),
)
def display_analyze_button(start_date: str, end_date: str) -> html:
    if start_date is None or end_date is None:
        return None
    return html.Div(
        [
            html.Button("Analyze", id="analyze-button", n_clicks=0, disabled=False),
            html.Div(id="analysis-container"),
        ]
    )


@dash.callback(
    Output("analysis-container", "children"), Input("analyze-button", "n_clicks")
)
def specify_analysis_container(analyze_button_clicks: int) -> html:
    if analyze_button_clicks == 0:
        return no_update

    return html.Div(
        [
            # analytic components:
            html.Div(id="seed-channel-metadata-table"),
            html.Div(id="domain-table-container"),
            html.Div(id="birth-chart-container"),
            dcc.RadioItems(
                id="birth-chart-unit",
                options=[
                    {"label": "Years", "value": "year"},
                    {"label": "Months", "value": "month"},
                    {"label": "Weeks", "value": "week"},
                    {"label": "Days", "value": "day"},
                    {"label": "Hours", "value": "hour"},
                    {"label": "Minutes", "value": "minute"},
                ],
                value="month",
            ),
            html.Br(),
            html.Div(id="time-series-chart-container"),
            dcc.RadioItems(
                id="time-series-chart-unit",
                options=[
                    {"label": "Years", "value": "year"},
                    {"label": "Months", "value": "month"},
                    {"label": "Weeks", "value": "week"},
                    {"label": "Days", "value": "day"},
                    {"label": "Hours", "value": "hour"},
                    {"label": "Minutes", "value": "minute"},
                ],
                value="day",
            ),
            html.Br(),
            html.Div(id="message-table-container"),
        ]
    )


@dash.callback(
    Output("seed-channel-metadata-table", "children"),
    Input("seed-channel-metadata-table", "children"),
    State("seed-list-menu", "value"),
)
def print_channel_metadata_table(
    seed_table_children: html, seed_list_names: list[str]
) -> html:
    records = get_seed_channel_metadata(seed_list_names)

    return html.Div(
        [
            dash_table.DataTable(
                data=records,
                columns=[{"name": key, "id": key} for key in records[0].keys()],
                style_cell={"textAlign": "left"},
                page_current=0,
                page_size=10,
                export_format="csv",
                sort_action="native",
            )
        ]
    )


@dash.callback(
    Output("birth-chart-container", "children"),
    Input("birth-chart-unit", "value"),
    State("seed-list-menu", "value"),
)
def render_birth_chart(birth_chart_unit: str, seed_list_names: list[str]) -> html:
    records = get_birth_chart_data(birth_chart_unit, seed_list_names)

    fig = px.bar(records, x="creation_dt", y="count")
    fig.update_layout(
        title_text="Seed channel birthdates",
        xaxis_title_text="Date/time",
        yaxis_title_text="Number of births",
        template="plotly_dark",
    )
    return dcc.Graph(id="seed-channel-birth-chart", figure=fig)


@dash.callback(
    Output("time-series-chart-container", "children"),
    Input("time-series-chart-unit", "value"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def render_time_series_chart(
    time_series_chart_unit: str,
    seed_list_names: list[str],
    start_date: str,
    end_date: str,
) -> html:
    df = pd.DataFrame.from_records(
        get_time_series_chart_data(
            start_date, end_date, time_series_chart_unit, seed_list_names
        )
    )

    if df.shape[0] == 0:
        return html.Div(
            [
                html.P(
                    "Cannot display time series chart (no messages found for these seeds and this date range).",
                    style={"color": "red"},
                )
            ]
        )

    fig = px.line(df, x="message_dt", y="count")
    fig.update_layout(
        title_text=f"Seed channel message counts ({df['count'].sum()} total)",
        xaxis_title_text="Date/time",
        yaxis_title_text="Number of Messages",
        template="plotly_dark",
    )
    return html.Div([dcc.Graph(id="time-series-chart", figure=fig)])


@dash.callback(
    Output("message-table-container", "children"),
    Input("message-table-container", "children"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def render_message_table_callback(
    message_table_children: html,
    seed_list_names: list[str],
    start_date: str,
    end_date: str,
) -> html:
    records = render_message_table(start_date, end_date, seed_list_names)

    if len(records) == 0:
        return html.Div(
            [
                html.P(
                    "Cannot display message table (no messages found for these seeds and this date range).",
                    style={"color": "red"},
                )
            ]
        )

    return html.Div(
        [
            html.Button(
                "Translate messages to English",
                id="translate-button",
                n_clicks=0,
                disabled=False,
            ),
            dash_table.DataTable(
                id="message-table",
                data=records,
                columns=[
                    {"name": key, "id": key, "type": "text", "presentation": "markdown"}
                    if key == "url"
                    else {"id": key, "name": key}
                    for key in records[0].keys()
                ],
                style_cell={"textAlign": "left"},
                style_data={
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                page_current=0,
                page_size=10,
                export_format="csv",
                sort_action="native",
            ),
        ]
    )


@dash.callback(
    Output("message-table", "data"),
    Output("message-table", "columns"),
    Input("translate-button", "n_clicks"),
    State("message-table", "data"),
)
def translate_messages_callback(
    num_clicks: int, records: list[dict]
) -> (list[dict], list[dict]):
    if num_clicks == 0:
        return no_update, no_update

    # Translate messages
    records = translate_messages(records)

    return records, [
        {"name": key, "id": key, "type": "text", "presentation": "markdown"}
        if key == "url"
        else {"id": key, "name": key}
        for key in records[0].keys()
    ]
