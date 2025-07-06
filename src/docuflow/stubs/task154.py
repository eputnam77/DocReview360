"""Return a minimal GraphQL Explorer page (Task 154)."""

from __future__ import annotations

from . import record_task_completion


def task154(api_url: str = "/graphql") -> str:
    """Return HTML for an embedded GraphiQL explorer."""

    script = (
        "<script>const fetcher=GraphiQL.createFetcher({url:'" + api_url + "'});"
        "ReactDOM.render(React.createElement(GraphiQL,{fetcher:fetcher}),"
        "document.getElementById('graphiql'));</script>"
    )
    html = (
        "<html><body><div id='graphiql'></div>"
        "<link rel='stylesheet' href='https://unpkg.com/graphiql/graphiql.min.css'>"
        "<script crossorigin src='https://unpkg.com/graphiql/graphiql.min.js'></script>"
        + script
        + "</body></html>"
    )
    record_task_completion(154)
    return html
