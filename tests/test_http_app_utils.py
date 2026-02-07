import importlib
import sys
import types


def _load_http_app(monkeypatch):
    starlette_applications = types.ModuleType("starlette.applications")
    starlette_requests = types.ModuleType("starlette.requests")
    starlette_responses = types.ModuleType("starlette.responses")
    starlette_routing = types.ModuleType("starlette.routing")

    class FakeStarlette:
        def __init__(self, routes=None, lifespan=None):
            self.routes = routes or []
            self.lifespan = lifespan

    class FakeRequest:
        def __init__(self, headers, base_url="http://localhost/"):
            self.headers = headers
            self.base_url = base_url

    class FakeResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class FakeRoute:
        def __init__(self, path, endpoint, methods=None):
            self.path = path
            self.endpoint = endpoint
            self.methods = methods

    class FakeMount:
        def __init__(self, path, app):
            self.path = path
            self.app = app

    starlette_applications.Starlette = FakeStarlette
    starlette_requests.Request = FakeRequest
    starlette_responses.FileResponse = FakeResponse
    starlette_responses.JSONResponse = FakeResponse
    starlette_responses.RedirectResponse = FakeResponse
    starlette_routing.Route = FakeRoute
    starlette_routing.Mount = FakeMount

    monkeypatch.setitem(sys.modules, "starlette.applications", starlette_applications)
    monkeypatch.setitem(sys.modules, "starlette.requests", starlette_requests)
    monkeypatch.setitem(sys.modules, "starlette.responses", starlette_responses)
    monkeypatch.setitem(sys.modules, "starlette.routing", starlette_routing)

    mcp_server_stub = types.ModuleType("mcp_atomictoolkit.mcp_server")

    class FakeMCP:
        def http_app(self, **kwargs):
            async def app(scope, receive, send):
                return None

            return app

    mcp_server_stub.mcp = FakeMCP()
    monkeypatch.setitem(sys.modules, "mcp_atomictoolkit.mcp_server", mcp_server_stub)

    sys.modules.pop("mcp_atomictoolkit.http_app", None)
    return importlib.import_module("mcp_atomictoolkit.http_app")


def test_accept_header_compat_adds_json(monkeypatch):
    http_app = _load_http_app(monkeypatch)

    seen = {}

    async def app(scope, receive, send):
        seen["headers"] = scope.get("headers", [])

    wrapper = http_app._AcceptHeaderCompatApp(app)
    scope = {
        "type": "http",
        "headers": [(b"host", b"example.test")],
    }

    import asyncio

    asyncio.run(wrapper(scope, None, None))
    assert any(name == b"accept" for name, _ in seen["headers"])


def test_accept_header_compat_replaces_invalid(monkeypatch):
    http_app = _load_http_app(monkeypatch)

    seen = {}

    async def app(scope, receive, send):
        seen["headers"] = scope.get("headers", [])

    wrapper = http_app._AcceptHeaderCompatApp(app)
    scope = {
        "type": "http",
        "headers": [(b"accept", b"text/plain")],
    }

    import asyncio

    asyncio.run(wrapper(scope, None, None))
    accept = dict(seen["headers"]).get(b"accept")
    assert accept == b"application/json, text/event-stream"


def test_public_base_url_prefers_forwarded_headers(monkeypatch):
    http_app = _load_http_app(monkeypatch)
    request = http_app.Request(
        {"x-forwarded-proto": "https", "x-forwarded-host": "example.test"},
        base_url="http://ignored/",
    )
    assert http_app._public_base_url(request) == "https://example.test"


def test_public_base_url_falls_back_to_request_base(monkeypatch):
    http_app = _load_http_app(monkeypatch)
    request = http_app.Request({}, base_url="http://local.test/root/")
    assert http_app._public_base_url(request) == "http://local.test/root"
