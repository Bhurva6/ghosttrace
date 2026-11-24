"""Deterministic incident reconstruction.

Rules: every claim cites event ids. A hypothesis is never evidence.
Facts = things in the logs. Hypotheses = explanations, with support,
contradictions and unknowns listed separately.
"""
import json
from datetime import datetime, timedelta

GAP_SECONDS = 300          # silence from a service longer than this is flagged
RETRY_STORM_MIN = 5        # retries to one target inside the window
RETRY_WINDOW = 60
SYMPTOM_LEVELS = {"ERROR", "FATAL"}


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_events(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return validate(data["events"] if isinstance(data, dict) else data)


def validate(events):
    seen, out = set(), []
    for e in events:
        for k in ("id", "ts", "service", "level", "msg"):
            if k not in e:
                raise ValueError(f"event missing '{k}': {e}")
        if e["id"] in seen:
            raise ValueError(f"duplicate event id {e['id']}")
        seen.add(e["id"])
        e = dict(e)
        e["_t"] = _t(e["ts"])
        e.setdefault("attrs", {})
        out.append(e)
    return sorted(out, key=lambda e: (e["_t"], e["id"]))


def timeline(events):
    """Facts only: first error per service, deploys, config changes, gaps."""
    items, first_err = [], {}
    for e in events:
        kind = e["attrs"].get("kind")
        if kind in ("deploy", "config_change", "rollback"):
            items.append(_item(e, kind))
        if e["level"] in SYMPTOM_LEVELS and e["service"] not in first_err:
            first_err[e["service"]] = e
            items.append(_item(e, "first_error"))
    by_svc = {}
    for e in events:
        by_svc.setdefault(e["service"], []).append(e)
    for svc, evs in by_svc.items():
        for a, b in zip(evs, evs[1:]):
            if (b["_t"] - a["_t"]).total_seconds() > GAP_SECONDS:
                items.append({"ts": a["ts"], "kind": "log_gap", "service": svc,
                              "text": f"No logs from {svc} for {int((b['_t']-a['_t']).total_seconds())}s",
                              "evidence": [a["id"], b["id"]]})
    return sorted(items, key=lambda i: i["ts"])


def _item(e, kind):
    return {"ts": e["ts"], "kind": kind, "service": e["service"], "text": e["msg"], "evidence": [e["id"]]}


def _hyp(name, summary, conf, support, contra, unknowns, tests):
    return {"name": name, "summary": summary, "confidence": conf, "supporting": support,
            "contradicting": contra, "unknowns": unknowns, "suggested_tests": tests,
            "status": "hypothesis, needs human review"}


def _first_symptom(events):
    for e in events:
        if e["level"] in SYMPTOM_LEVELS:
            return e
    return None


def hypotheses(events):
    out = []
    sym = _first_symptom(events)
    deploys = [e for e in events if e["attrs"].get("kind") == "deploy"]

    # 1. deploy failure: errors on the deployed service soon AFTER the deploy
    for d in deploys:
        after = [e for e in events if e["service"] == d["service"] and e["level"] in SYMPTOM_LEVELS
                 and timedelta(0) <= e["_t"] - d["_t"] <= timedelta(minutes=10)]
        before = [e for e in events if e["service"] == d["service"] and e["level"] in SYMPTOM_LEVELS and e["_t"] < d["_t"]]
        if len(after) >= 2:
            contra = [e["id"] for e in before]
            conf = "low" if before else "medium"
            unk = ["Deploy diff not in logs", "Whether a rollback was tried"]
            if before:
                unk.insert(0, "Errors predate the deploy, so it may be a coincidence")
            out.append(_hyp("deploy_failure", f"Deploy {d['attrs'].get('version','?')} to {d['service']} may have introduced the errors.",
                            conf, [d["id"]] + [e["id"] for e in after[:5]], contra, unk,
                            [f"{d['service']} starts cleanly with config from release {d['attrs'].get('version','?')}"]))

    # 2. retry storm
    groups = {}
    for e in events:
        if e["attrs"].get("kind") == "retry":
            groups.setdefault((e["service"], e["attrs"].get("target")), []).append(e)
    for (svc, target), evs in groups.items():
        for i, e in enumerate(evs):
            win = [x for x in evs[i:] if (x["_t"] - e["_t"]).total_seconds() <= RETRY_WINDOW]
            if len(win) >= RETRY_STORM_MIN:
                backoff = all(b["attrs"].get("delay_ms", 0) > a["attrs"].get("delay_ms", 0) for a, b in zip(win, win[1:]))
                out.append(_hyp("retry_storm", f"{svc} hammered {target} with {len(win)} retries in {RETRY_WINDOW}s; may amplify the outage.",
                                "medium" if not backoff else "low", [x["id"] for x in win],
                                [x["id"] for x in win] if backoff else [],
                                ["Whether {t} was already down before retries".format(t=target), "Client retry config not in logs"],
                                [f"{svc} backs off exponentially with jitter when {target} fails"]))
                break

    # 3. credential expiry
    cred = [e for e in events if e["attrs"].get("status") in (401, 403) or "token expired" in e["msg"].lower() or "credential" in e["msg"].lower() and e["level"] in SYMPTOM_LEVELS]
    if cred:
        rot = [e for e in events if "rotat" in e["msg"].lower()]
        out.append(_hyp("credential_expiry", "Authentication failures suggest an expired or rotated credential.",
                        "high" if rot else "medium", [e["id"] for e in cred[:6]] + [e["id"] for e in rot], [],
                        ["Who owns the credential", "Whether rotation was planned"],
                        ["Expired credential produces a clear alert before the first 401 outage"]))

    # sanity: a cause must not start after the first symptom
    if sym:
        for h in out:
            starts = min(e["_t"] for e in events if e["id"] in h["supporting"])
            if starts > sym["_t"] + timedelta(minutes=1):
                h["confidence"] = "low"
                h["unknowns"].append("Support begins after the first symptom, so this may be an effect")
    return out


def analyze(events):
    gaps = [i for i in timeline(events) if i["kind"] == "log_gap"]
    return {
        "summary": {"events": len(events), "services": sorted({e["service"] for e in events}),
                    "first_symptom": (_first_symptom(events) or {}).get("id")},
        "evidence_timeline": timeline(events),
        "hypotheses": hypotheses(events),
        "missing_data": gaps,
        "note": "Evidence lists events from the logs. Hypotheses are guesses and need human review.",
    }
