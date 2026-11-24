# GhostTrace

Replay an incident from logs. GhostTrace builds a timeline from what the logs actually say, then lists possible causes as hypotheses. It never presents a guess as a fact.

## What it does
- Reads JSON event logs (synthetic fixtures included).
- **Evidence timeline**: deploys, config changes, first error per service, and gaps where a service went silent. Every line cites event ids.
- **Hypotheses**: deploy failure, retry storm, credential expiry. Each lists supporting events, contradicting events, unknowns, and a suggested regression test. Nothing is applied without a human.
- **Misleading correlation guard**: a deploy that happens after the errors started is downgraded to low confidence.
- Dark "ghost" themed HTML report.

## Run
    python3 -m ghosttrace.report fixtures/deploy_failure.json --html out.html
    python3 -m unittest discover -s tests

Python 3.8+, no dependencies.

## Data
All logs are synthetic. No real incident data, no employer code.

## Kiro files
Spec, steering and hook notes live in `.kiro/`. They were written by hand as a plan for the project; a Kiro IDE/CLI pass has not been run yet.

## Limits
Rule-based, not a model. It finds three failure patterns and says "no hypothesis" when none fit.
