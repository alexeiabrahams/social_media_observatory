from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash
import plotly.express as px

import dash_cytoscape as cyto

import pandas as pd

from datetime import date


from ...utilities.logic_ch4 import (
    get_names_of_seed_lists,
    get_seed_list_preview,
    get_seed_channel_metadata,
    get_birth_chart_data,
    get_time_series_chart_data,
    render_message_table,
    translate_messages,
    make_forward_network,
    make_cytoscape_elements,
    make_domain_network,
    make_domain_table,
    make_cytoscape_stylesheet,
    get_metadata_for_single_channel,
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
def specify_analysis_container(analyze_button_clicks):
    if analyze_button_clicks == 0:
        return no_update

    return html.Div(
        [
            # analytic components:
            html.Div(id="seed-channel-metadata-table"),
            html.Div(id="forward-network-container"),
            html.Div(id="domain-network-container"),
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


@dash.callback(
    Output("forward-network-container", "children"),
    Input("forward-network-container", "children"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def render_forward_network(
    message_table_children, seed_list_names, start_date, end_date
):
    G = make_forward_network(seed_list_names, start_date, end_date, 800)
    my_elements = make_cytoscape_elements(G, "count_1")
    my_stylesheet = make_cytoscape_stylesheet(my_elements)

    return html.Div(
        [
            html.P(
                f"Forwarding network has {len(G.nodes())} nodes and {len(G.edges())} edges"
            ),
            cyto.Cytoscape(
                id="forward-network",
                layout={"name": "cose"},
                style={"width": "90%", "height": "800px"},
                elements=my_elements,
                stylesheet=my_stylesheet,
                responsive=True,
            ),
            html.Br(),
            html.Div(id="tapNode-feedback"),
        ]
    )


@dash.callback(
    Output("domain-network-container", "children"),
    Input("domain-network-container", "children"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def render_domain_network(
    domain_network_container, seed_list_names, start_date, end_date
):
    B = make_domain_network(seed_list_names, start_date, end_date, 800)
    my_elements = make_cytoscape_elements(B, "weight", "label")
    my_stylesheet = make_cytoscape_stylesheet(my_elements)

    return html.Div(
        [
            html.P(
                f"Domain network has {len(B.nodes())} nodes and {len(B.edges())} edges"
            ),
            cyto.Cytoscape(
                id="domain-network",
                layout={"name": "cose"},
                style={"width": "90%", "height": "800px"},
                elements=my_elements,
                stylesheet=my_stylesheet,
                responsive=True,
            ),
            html.Br(),
            html.Div(id="domain-tapNode-feedback"),
        ]
    )


@dash.callback(
    Output("domain-table-container", "children"),
    Input("domain-table-container", "children"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def render_domain_table(domain_table_container, seed_list_names, start_date, end_date):
    domain_records = make_domain_table(seed_list_names, start_date, end_date)

    return html.Div(
        [
            dash_table.DataTable(
                data=domain_records,
                columns=[
                    {"name": key, "id": key, "type": "text", "presentation": "markdown"}
                    if key == "domain"
                    else {"id": key, "name": key}
                    for key in domain_records[0].keys()
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
            )
        ]
    )


@dash.callback(
    Output("forward-network", "stylesheet"),
    Input("forward-network", "mouseoverNodeData"),
    State("forward-network", "elements"),
)
def change_transparency_forward_network(hovered_node, my_elements):
    if not hovered_node:
        return no_update

    return make_cytoscape_stylesheet(my_elements, hovered_node)


@dash.callback(
    Output("domain-network", "stylesheet"),
    Input("domain-network", "mouseoverNodeData"),
    State("domain-network", "elements"),
)
def change_transparency_domain_network(hovered_node, my_elements):
    if not hovered_node:
        return no_update

    my_stylesheet = make_cytoscape_stylesheet(my_elements, hovered_node)

    return my_stylesheet


@dash.callback(
    Output("tapNode-feedback", "children"),
    Input("forward-network", "tapNodeData"),
    State("seed-list-menu", "value"),
    State("my-date-picker-range", "start_date"),
    State("my-date-picker-range", "end_date"),
)
def print_information_after_click(node_data, seed_list_names, start_date, end_date):
    if not node_data:
        return no_update

    metadata_df = pd.DataFrame.from_records(
        get_metadata_for_single_channel(node_data["id"])
    )

    if metadata_df.empty:
        return html.Div(
            html.P(
                f"The node you clicked on has ID {node_data['id']}. "
                f"The database contains no further information on it."
            )
        )

    return html.Div(
        [
            html.P(f"Here is some metadata on the channel you clicked on:"),
            dash_table.DataTable(
                data=metadata_df.to_dict("records"),
                columns=[{"name": i, "id": i} for i in list(metadata_df)],
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
