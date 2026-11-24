import os, unittest, copy
from ghosttrace import analyze, load_events
from ghosttrace.engine import validate
from ghosttrace.report import render
F = os.path.join(os.path.dirname(__file__), "..", "fixtures")
def run(n): return analyze(load_events(os.path.join(F, n + ".json")))
def names(r): return [h["name"] for h in r["hypotheses"]]

class T(unittest.TestCase):
    def test_deploy(self):
        r = run("deploy_failure"); self.assertIn("deploy_failure", names(r))
        h = r["hypotheses"][0]; self.assertEqual(h["confidence"], "medium"); self.assertEqual(h["contradicting"], [])
    def test_retry(self):
        r = run("retry_storm"); self.assertIn("retry_storm", names(r))
    def test_cred_high_with_rotation(self):
        r = run("credential_expiry"); self.assertEqual(r["hypotheses"][0]["confidence"], "high")
    def test_misleading_correlation_downgraded(self):
        r = run("misleading_correlation"); h = [h for h in r["hypotheses"] if h["name"] == "deploy_failure"]
        self.assertTrue(h); self.assertEqual(h[0]["confidence"], "low"); self.assertIn("e1", h[0]["contradicting"])
    def test_missing_logs_flagged(self):
        r = run("missing_logs"); self.assertEqual(len(r["missing_data"]), 1); self.assertEqual(r["missing_data"][0]["service"], "cache")
    def test_no_hypothesis_is_ok(self):
        r = run("missing_logs"); self.assertEqual(r["hypotheses"], [])
    def test_all_cited_ids_exist(self):
        for n in ["deploy_failure","retry_storm","credential_expiry","misleading_correlation","missing_logs"]:
            r = run(n); ids = {e["id"] for e in load_events(os.path.join(F, n + ".json"))}
            for h in r["hypotheses"]: self.assertTrue(set(h["supporting"] + h["contradicting"]) <= ids)
            for i in r["evidence_timeline"]: self.assertTrue(set(i["evidence"]) <= ids)
    def test_hypotheses_marked_unverified(self):
        for h in run("deploy_failure")["hypotheses"]: self.assertIn("review", h["status"])
    def test_every_hypothesis_has_unknowns_and_test(self):
        for n in ["deploy_failure","retry_storm","credential_expiry"]:
            for h in run(n)["hypotheses"]: self.assertTrue(h["unknowns"] and h["suggested_tests"])
    def test_duplicate_id_rejected(self):
        e = {"id":"a","ts":"2026-01-01T00:00:00Z","service":"s","level":"INFO","msg":"m"}
        with self.assertRaises(ValueError): validate([e, dict(e)])
    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError): validate([{"id":"a"}])
    def test_unsorted_input_sorted(self):
        a = {"id":"a","ts":"2026-01-01T00:00:10Z","service":"s","level":"INFO","msg":"m"}
        b = dict(a, id="b", ts="2026-01-01T00:00:01Z"); self.assertEqual(validate([a, b])[0]["id"], "b")
    def test_empty_events(self):
        r = analyze([]); self.assertEqual(r["hypotheses"], []); self.assertEqual(r["summary"]["events"], 0)
    def test_html_escapes(self):
        e = {"id":"a","ts":"2026-01-01T00:00:00Z","service":"s","level":"FATAL","msg":"<script>x</script>"}
        out = render(analyze(validate([e]))); self.assertNotIn("<script>x", out)
    def test_html_has_both_sections(self):
        out = render(run("deploy_failure")); self.assertIn("Evidence (from the logs)", out); self.assertIn("Hypotheses (not evidence)", out)
    def test_retry_with_backoff_lower_confidence(self):
        evs = [{"id":f"r{i}","ts":f"2026-01-01T00:00:{i:02d}Z","service":"w","level":"WARN","msg":"retry","attrs":{"kind":"retry","target":"t","delay_ms":100*2**i}} for i in range(6)]
        h = analyze(validate(evs))["hypotheses"]; self.assertEqual(h[0]["confidence"], "low")
    def test_deterministic(self): self.assertEqual(run("deploy_failure"), run("deploy_failure"))
    def test_first_symptom(self): self.assertEqual(run("misleading_correlation")["summary"]["first_symptom"], "e1")
    def test_summary_services(self): self.assertEqual(run("deploy_failure")["summary"]["services"], ["api","db"])
    def test_cred_without_rotation_medium(self):
        evs = [{"id":"a","ts":"2026-01-01T00:00:00Z","service":"b","level":"ERROR","msg":"x","attrs":{"status":401}}]
        self.assertEqual(analyze(validate(evs))["hypotheses"][0]["confidence"], "medium")
if __name__ == "__main__": unittest.main()
