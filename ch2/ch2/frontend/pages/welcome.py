from dash import dcc, html

layout = html.Div(
    [
        html.Div(
            [
                html.H1("Welcome to the social media observatory!"),
                dcc.Link("Upload Telegram handles", href="/upload"),
            ]
        )
    ]
)
