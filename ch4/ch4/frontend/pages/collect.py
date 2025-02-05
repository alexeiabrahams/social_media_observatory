from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash

from ...utilities.logic_ch4 import (
    get_names_of_seed_lists,
    get_seed_list_preview,
    send_handles_to_tg_channel_messages_lookup_queue,
)

layout = html.Div(
    [
        html.H1("Collection page"),
        dcc.Dropdown(
            id="seed-list-menu-2",
            options=[],
            placeholder="Select your seed list(s)",
            style={"color": "black"},
            value=None,
            disabled=False,
            multi=False,
        ),
        html.Div(id="seed-list-menu-2-feedback"),
    ]
)


@dash.callback(
    Output("seed-list-menu-2", "options"), Input("seed-list-menu-2", "options")
)
def populate_menu_with_seed_lists(my_options: list[dict]) -> list[dict]:
    return [
        {"label": f"{my_seed_list}", "value": f"{my_seed_list}"}
        for my_seed_list in get_names_of_seed_lists()
    ]


@dash.callback(
    Output("seed-list-menu-2-feedback", "children"),
    Input("seed-list-menu-2", "value"),
)
def display_seed_list_preview_and_collect_buttons(my_seed_list: str) -> html:
    if my_seed_list is None:
        return no_update
    data = get_seed_list_preview([my_seed_list])

    return html.Div(
        [
            dash_table.DataTable(
                data=data,
                columns=[{"name": i, "id": i} for i in list(data[0].keys())],
                style_cell={"textAlign": "left"},
                page_current=0,
                page_size=10,
                export_format="csv",
                sort_action="native",
            ),
            dcc.Store(id="seed-channels", data=data),
            html.Button(
                "Collect channel messages",
                id="channel-messages-button",
                n_clicks=0,
                disabled=False,
            ),
            html.Div(id="button-click-feedback-container"),
        ]
    )


@dash.callback(
    Output("button-click-feedback-container", "children"),
    Input("channel-messages-button", "n_clicks"),
    State("seed-channels", "data"),
    State("seed-list-menu-2", "value"),
)
def on_collect_button_click(
    channel_messages_button: int, seed_data: list[dict], seed_list_name: str
) -> html:
    if channel_messages_button == 0:
        return None

    records = [
        {"handle": seed_data[i]["channel_name"], "seed_list": seed_list_name}
        for i in range(0, len(seed_data))
    ]

    # Push handles to queue
    send_handles_to_tg_channel_messages_lookup_queue(records)

    return html.Div(
        f"{len(seed_data)} channels pushed to the message collection queue!"
    )
