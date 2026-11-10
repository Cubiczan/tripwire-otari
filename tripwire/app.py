"""Local dashboard and HTTP API for the Tripwire-for-Otari demo."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tripwire.agent import Tripwire, load_pack, run_all
from tripwire.otari import load_settings

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard"

_gate: Tripwire | None = None
_scenarios: list[dict] = []


def get_gate() -> Tripwire:
    global _gate, _scenarios
    if _gate is None:
        policy, _scenarios = load_pack()
        _gate = Tripwire(policy=policy)
    return _gate


def create_app() -> FastAPI:
    app = FastAPI(title="Tripwire for Otari", version="0.1.0")

    @app.get("/api/status")
    def status():
        gate = get_gate()
        ok, bad = gate.audit.verify()
        settings = load_settings()
        return {
            "otari_mode": settings["mode"],
            "requested_mode": settings["requested_mode"],
            "has_key": settings["has_key"],
            "has_key_west": settings["has_key_west"],
            "base_url": settings["base_url"],
            "models": {
                "analyst": settings["model_analyst"],
                "verifier": settings["model_verifier"],
                "route": settings["model_route"],
            },
            "guardrail_profile": settings["guardrail_profile"],
            "decisions": len(gate.results),
            "open_holds": sum(1 for h in gate.holds.values() if h.status == "open"),
            "audit_ok": ok,
            "audit_broken_at": bad,
            "mock_banner": settings["mode"] != "live",
        }

    @app.get("/api/scenarios")
    def scenarios():
        get_gate()
        return {"scenarios": _scenarios or load_pack()[1]}

    @app.post("/api/run")
    def run_one(body: dict):
        gate = get_gate()
        scenario_id = body.get("scenario_id")
        policy, pack = load_pack()
        if gate.policy.allowed_payees != policy.allowed_payees:
            gate.policy = policy
        found = next((s for s in pack if s["id"] == scenario_id), None)
        if not found:
            raise HTTPException(404, "unknown_scenario")
        result = gate.run_scenario(found)
        return result.to_public_dict()

    @app.post("/api/run-all")
    def run_everything():
        # Fresh gate so the demo is repeatable from the dashboard.
        global _gate
        _gate, results = run_all()
        ok, bad = _gate.audit.verify()
        return {
            "mode": _gate.client.mode,
            "audit_ok": ok,
            "audit_broken_at": bad,
            "results": [r.to_public_dict() for r in results],
        }

    @app.get("/api/decisions")
    def decisions():
        gate = get_gate()
        return {"results": [r.to_public_dict() for r in gate.results]}

    @app.get("/api/holds")
    def holds():
        gate = get_gate()
        return {"holds": [h.__dict__ for h in gate.holds.values()]}

    @app.post("/api/holds/{hold_id}/approve")
    def approve(hold_id: str):
        return get_gate().approve(hold_id)

    @app.post("/api/holds/{hold_id}/deny")
    def deny(hold_id: str):
        return get_gate().deny_hold(hold_id)

    @app.get("/api/audit/verify")
    def audit_verify():
        gate = get_gate()
        ok, bad = gate.audit.verify()
        return {"ok": ok, "broken_at": bad, "entries": len(gate.audit.entries())}

    @app.get("/")
    def index():
        return FileResponse(DASHBOARD / "index.html")

    if DASHBOARD.exists():
        app.mount("/static", StaticFiles(directory=str(DASHBOARD)), name="static")
    return app


app = create_app()
