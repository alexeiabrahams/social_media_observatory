from ...config import handles_queue
from ...utilities.mq_ch2 import send_data_to_queue

from dash import dcc, html, Input, Output, State, dash_table, no_update
import dash

import base64
import io
import re
import pandas as pd

layout = html.Div(
    [
        html.Div(
            [
                dcc.Upload(
                    id="drag-and-drop",
                    children=html.Div(
                        [
                            f"Drag and drop your CSV here, or ",
                            html.A("click here to browse your file system"),
                        ]
                    ),
                    style={
                        "width": "99%",
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px",
                    },
                    multiple=False,
                ),
            ]
        ),
        html.Div(id="drag-and-drop-feedback"),
    ]
)


@dash.callback(
    Output("drag-and-drop-feedback", "children"),
    Input("drag-and-drop", "filename"),
    Input("drag-and-drop", "contents"),
)
def preview_file(filename: str, contents: list):
    if filename is None:
        return None
    if filename[filename.rfind(".") :] != ".csv":
        return html.P("Please upload a CSV", style={"color": "red"})

    # Load file
    content_type, content_b64_string = contents.split(",")
    content_decoded_string = base64.b64decode(content_b64_string)
    df = pd.read_csv(io.StringIO(content_decoded_string.decode("utf-8")))

    if "handle" not in list(df):
        return html.P(
            "Please include a column of handles entitled 'handle'",
            style={"color": "red"},
        )

    # Drop null rows
    df = df.loc[df["handle"].notnull(), :]

    # Convert to lowercase
    df["handle"] = df["handle"].apply(lambda x: x.lower())

    # De-duplicate
    df.drop_duplicates("handle", inplace=True)

    # Check if there are any rows left
    if df.empty:
        return html.P(
            "Please include at least one handle in the 'handle' column",
            style={"color": "red"},
        )

    # Check if handles contain illegal characters
    for i in df.index:
        if re.match(r"^\w+$", df.loc[i, "handle"]) is None:
            return html.P(
                f"""Illegal characters detected in row {i + 2} 
                of spreadsheet: {df.loc[i, 'handle']}""",
                style={"color": "red"},
            )

    return html.Div(
        [
            dash_table.DataTable(
                data=df.to_dict("records"),
                columns=[{"name": i, "id": i} for i in list(df)],
                style_cell={"textAlign": "left"},
                page_current=0,
                page_size=10,
            ),
            html.Div(
                [
                    html.H4(
                        children="Enter seed list name (case-insensitive):",
                        style={"color": "blue"},
                    ),
                    dcc.Input(
                        id="seed-list-name",
                        type="text",
                        placeholder="No special characters!",
                        disabled=False,
                        debounce=False,
                        value=filename.rstrip(".csv").lower(),
                    ),
                    html.Div(id="seed-list-name-response"),
                ]
            ),
            dcc.Store(id="seed-data", data=df.to_dict("records")),
        ]
    )


@dash.callback(
    Output("seed-list-name-response", "children"), Input("seed-list-name", "value")
)
def validate_seed_list_name(seed_list_name: str):
    if not seed_list_name:
        return dash.no_update

    if re.match(r"^\w+$", seed_list_name) is None:
        return html.P(
            f"""Use only alphanumeric characters or underscores""",
            style={"color": "red"},
        )
    if len(seed_list_name) > 64:
        return html.P(f"""Use <=64 chars""", style={"color": "red"})

    return html.Div(
        [
            html.Button(
                "Upload to server", id="upload-button", n_clicks=0, disabled=False
            ),
            html.Div(id="upload-feedback"),
        ]
    )


@dash.callback(
    Output("upload-button", "n_clicks"),
    Output("upload-feedback", "children"),
    Input("upload-button", "n_clicks"),
    State("seed-data", "data"),
    State("seed-list-name", "value"),
)
def upload_file(want_upload: int, seed_data: list[dict], seed_list_name: str):
    if want_upload == 0:
        return no_update, no_update

    # Load data from cache
    df = pd.DataFrame.from_records(seed_data)

    # Define messages to send to queue
    messages = [
        {"handles": [handle], "seed_list": seed_list_name.lower()}
        for handle in list(df["handle"])
    ]

    # Send messages to queue
    send_data_to_queue(messages, handles_queue)

    return 0, html.P(
        f"Seed list '{seed_list_name}' submitted for data collection!",
        style={"color": "lime"},
    )
