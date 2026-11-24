# Requirements (EARS)
1. WHEN a log file is loaded, THE SYSTEM SHALL reject duplicate ids and missing fields.
2. WHEN events are analyzed, THE SYSTEM SHALL produce a timeline where every item cites existing event ids.
3. WHEN a service is silent longer than 300s, THE SYSTEM SHALL flag a log gap.
4. WHEN a deploy follows the first symptom, THE SYSTEM SHALL mark a deploy hypothesis low confidence.
5. THE SYSTEM SHALL label every hypothesis as needing human review and list its unknowns.
