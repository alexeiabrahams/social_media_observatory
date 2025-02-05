from dash import dcc, html

layout = html.Div(
    [
        html.Div(
            [
                html.H1("Welcome to the social media observatory!"),
                dcc.Link("Upload Telegram handles", href="/upload"),
                html.Br(),
                dcc.Link("Collect Telegram handles", href="/collect"),
                html.Br(),
                dcc.Link("Analyze Telegram data", href="/analyze"),
            ]
        )
    ]
)
