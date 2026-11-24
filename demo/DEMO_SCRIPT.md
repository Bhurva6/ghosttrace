# GhostTrace demo script (target 2:30, limit 3:00) (draft)
0:00 "Incidents are noisy and people jump to a cause. GhostTrace keeps what the logs say apart from what we guess."
0:15 Run the deploy_failure fixture, open the HTML report. Point at the Evidence section: each line cites event ids.
0:45 Scroll to Hypotheses: deploy failure, medium confidence, unknowns listed, suggested test needs approval.
1:15 Open misleading_correlation: errors began before the deploy. Confidence drops to low and the contradicting event is shown.
1:45 Open missing_logs: a silent cache is flagged as a finding, and no hypothesis is offered.
2:05 Show the .kiro/ spec and steering notes and the 20 passing tests (say only what is true about how Kiro was used).
2:25 "Evidence, hypotheses, unknowns. Synthetic data only."
