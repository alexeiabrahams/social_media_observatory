from dash import Dash, dcc, html, Input, Output
import dash

import secrets
from .pages import welcome, upload, collect, analyze

app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
server.secret_key = secrets.token_hex()

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)


@dash.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/":
        return welcome.layout
    elif pathname == "/upload":
        return upload.layout
    elif pathname == "/collect":
        return collect.layout
    elif pathname == "/analyze":
        return analyze.layout
    else:
        return "404"


def run():
    app.run_server(debug=True, use_reloader=False)

if __name__ == "__main__":
    run()
