import importlib
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_collab_endpoint_requires_y_py(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as context:
        context.setitem(sys.modules, "y_py", None)
        sys.modules.pop("docreview360.collab", None)
        collab = importlib.import_module("docreview360.collab")

        assert not getattr(collab, "YPY_AVAILABLE", True)

        app = FastAPI()
        app.include_router(collab.router)
        client = TestClient(app)

        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect("/collab/abc123"):
                pass

        assert excinfo.value.code == 1013
        assert "y_py" in collab.MISSING_DEPENDENCY_MESSAGE

    # Ensure subsequent imports use the actual implementation once available
    sys.modules.pop("docreview360.collab", None)
