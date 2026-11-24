import html, json, sys
from .engine import analyze, load_events

CSS = """body{background:#120d1f;color:#e8e2f5;font:15px/1.5 system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}
h1{color:#b794f6;letter-spacing:.05em}h2{border-bottom:1px solid #3b2d5c;padding-bottom:.3rem;margin-top:2rem}
.ev{border-left:3px solid #6ee7b7;padding:.3rem .8rem;margin:.4rem 0;background:#1b1430}
.hy{border-left:3px solid #f6ad55;padding:.3rem .8rem;margin:.6rem 0;background:#241a38}
.gap{border-left:3px solid #fc8181;padding:.3rem .8rem;margin:.4rem 0;background:#2a1730}
code{color:#fbd38d}.tag{font-size:.75em;border:1px solid #6b5a99;border-radius:4px;padding:0 .4em;margin-left:.4em}"""


def render(res):
    e = html.escape
    p = [f"<!doctype html><meta charset=utf-8><title>GhostTrace</title><style>{CSS}</style><h1>GHOSTTRACE</h1>",
         f"<p>{res['summary']['events']} events, services: {e(', '.join(res['summary']['services']))}. {e(res['note'])}</p>",
         "<h2>Evidence (from the logs)</h2>"]
    for i in res["evidence_timeline"]:
        cls = "gap" if i["kind"] == "log_gap" else "ev"
        p.append(f"<div class={cls}><code>{e(i['ts'])}</code> <b>{e(i['service'])}</b> <span class=tag>{e(i['kind'])}</span> {e(i['text'])} <small>[{e(', '.join(i['evidence']))}]</small></div>")
    p.append("<h2>Hypotheses (not evidence)</h2>")
    for h in res["hypotheses"]:
        p.append(f"<div class=hy><b>{e(h['name'])}</b> <span class=tag>confidence: {e(h['confidence'])}</span><br>{e(h['summary'])}<br>"
                 f"<small>Supporting: {e(', '.join(h['supporting']))}<br>Contradicting: {e(', '.join(h['contradicting']) or 'none found')}<br>"
                 f"Unknown: {e('; '.join(h['unknowns']))}<br>Suggested regression test (needs your approval): {e('; '.join(h['suggested_tests']))}</small></div>")
    if not res["hypotheses"]:
        p.append("<p>No hypothesis passes the rules. That is a valid result.</p>")
    return "\n".join(p)


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python -m ghosttrace.report fixtures/deploy_failure.json [--html out.html]"); return 2
    res = analyze(load_events(argv[0]))
    if "--html" in argv:
        open(argv[argv.index("--html") + 1], "w", encoding="utf-8").write(render(res))
    else:
        print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
