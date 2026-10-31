"""Optional NiceGUI mock integration prototype.

Requires the optional ``nicegui`` package. This source uses only MockAdapter and
must not be presented as vendor or Windows COM support.
"""
try:
    from nicegui import ui
except ImportError as exc:  # pragma: no cover - dependency is intentionally optional
    raise SystemExit("NiceGUI is not installed; install it in an isolated environment to run this mock prototype") from exc

from mcvar_sdk import AcquisitionClient, MockAdapter

client = AcquisitionClient(MockAdapter({"$DEMO.TEMPERATURE": 21.5, "$DEMO.MODE": "ready"}))
status = ui.label("Mock acquisition ready")
value = ui.label()


def refresh():
    result = client.read(["$DEMO.TEMPERATURE", "$DEMO.MODE"])
    value.text = " | ".join(f"{item.address}: {item.value} ({item.quality.value})" for item in result.items)


ui.button("Refresh", on_click=refresh)
refresh()
ui.run(title="MCVar SDK mock")
