from flask import Request


def client_wants_html(request: Request) -> bool:
    """True when a browser navigates to a frontend path (not the JSON API)."""
    if request.method != "GET":
        return False
    if request.args:
        return False
    return (
        request.accept_mimetypes.best_match(["application/json", "text/html"])
        == "text/html"
    )
