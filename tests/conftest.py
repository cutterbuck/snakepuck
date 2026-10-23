import json

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db


@pytest.fixture(scope="session")
def server():
    return create_app()


@pytest.fixture(scope="session")
def client(server):
    return server.test_client()


@pytest.fixture(scope="session")
def dash(client):
    return DashClient(client)


@pytest.fixture(scope="session")
def db_available(server):
    try:
        with server.app_context():
            db.session.execute(text("select 1"))
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_without_db(request, db_available):
    if request.node.get_closest_marker("db") and not db_available:
        pytest.skip("local Postgres unreachable")


@pytest.fixture
def app_ctx(server):
    with server.app_context():
        yield


def _output_parts(output):
    """Split a Dash output key into 'id.prop' parts, dropping @hash suffixes."""
    if output.startswith(".."):
        parts = output.strip(".").split("...")
    else:
        parts = [output]
    return [p.split("@")[0] for p in parts]


class DashClient:
    """Calls Dash callbacks over HTTP the way the browser does.

    Callbacks are looked up by their exact list of outputs; inputs and state
    are passed as {"id.prop": value} and default to None when omitted.
    """

    def __init__(self, client):
        self.client = client
        self.deps = client.get("/_dash-dependencies").get_json()

    def find(self, outputs):
        matches = [d for d in self.deps if _output_parts(d["output"]) == outputs]
        assert len(matches) == 1, (
            f"expected one callback for {outputs}, got {len(matches)}"
        )
        return matches[0]

    def call(self, outputs, inputs=None, state=None):
        """Return {"id.prop": value} for the callback's outputs, or None on PreventUpdate."""
        inputs, state = inputs or {}, state or {}
        dep = self.find(outputs)

        def _props(specs, values):
            return [
                {
                    "id": s["id"],
                    "property": s["property"],
                    "value": values.get(f"{s['id']}.{s['property']}"),
                }
                for s in specs
            ]

        out_specs = [
            {"id": p.rsplit(".", 1)[0], "property": p.rsplit(".", 1)[1]}
            for p in outputs
        ]
        body = {
            "output": dep["output"],
            "outputs": out_specs if len(out_specs) > 1 else out_specs[0],
            "inputs": _props(dep["inputs"], inputs),
            "state": _props(dep["state"], state),
            "changedPropIds": [
                f"{dep['inputs'][0]['id']}.{dep['inputs'][0]['property']}"
            ],
        }
        resp = self.client.post(
            "/_dash-update-component",
            data=json.dumps(body),
            content_type="application/json",
        )
        if resp.status_code == 204:
            return None
        assert resp.status_code == 200, resp.get_data(as_text=True)[:500]
        result = {}
        for comp_id, props in resp.get_json()["response"].items():
            for prop, value in props.items():
                result[f"{comp_id}.{prop}"] = value
        return result
