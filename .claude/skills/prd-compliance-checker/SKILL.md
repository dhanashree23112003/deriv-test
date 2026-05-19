Checks a completed project against the original PRD or spec to verify nothing is missing, nothing extra was added, and everything matches requirements exactly. Use at the end of implementation before submission. Triggers on: "check my project against the PRD", "am I missing anything", "does my project match the requirements", "run compliance check", "verify my submission", "check before I submit".PRD Compliance Checker
Reads the original PRD and the completed project, then produces a structured
gap analysis report before submission.

Step 1 — Read the PRD
Read Project_PRD.md fully and extract:

Every MUST COMPLETE requirement
Every SHOULD ATTEMPT requirement
Every STRETCH requirement
Every required artifact (file that must exist)
Every controlled vocabulary that must be validated
Every validation check that validate.py must perform
Every stage in the pipeline that must exist
Every LLM call that must be separate and logged
Every schema field that must be present in output files


Step 2 — Read the Project
Scan the entire project folder and extract:

All files that exist
All pipeline stages implemented
All artifacts generated (run the pipeline first if artifacts are missing)
All LLM calls logged in llm_calls.jsonl
All validation checks in validate.py
All controlled vocabularies defined in code


Step 3 — Run Validation
Run the project's own validation command:
bashpython validate.py
or
bashmake validate
Capture the full output.

Step 4 — Cross-Check Against PRD
For every requirement in the PRD, check if it is:

IMPLEMENTED: present and working
MISSING: required but not found
PARTIAL: started but incomplete
EXTRA: implemented but not in PRD (scope creep)

Check specifically:
Pipeline stages:

Every stage in the PRD state machine exists in code
Stage ordering is enforced (later stages cannot run before earlier ones)
Each stage saves its artifact before advancing state

LLM calls:

Every required LLM call exists as a separate API call
Every call is logged in llm_calls.jsonl with all required fields
No two required stages share a single LLM call

Artifacts:

Every required file exists
Every required JSON field is present in each artifact
No required field is null or empty when it should have a value

Controlled vocabularies:

Every vocabulary defined in PRD is validated in code
LLM outputs are checked against vocabularies after every call
Invalid values are rejected or retried, not silently accepted

Validate.py:

Every validation check listed in the PRD is present
Validation exits non-zero on failure
Validation covers all required artifacts

Schemas:

Every JSON schema in the PRD has a matching implementation
No fields were dropped or renamed without equivalent coverage


Step 5 — Produce the Report
Output a structured report with these exact sections:
MUST COMPLETE
For each requirement:

STATUS: DONE / MISSING / PARTIAL
Evidence: what file or code covers it (or what is missing)

SHOULD ATTEMPT
For each requirement:

STATUS: DONE / SKIPPED / PARTIAL
Evidence or reason skipped

STRETCH
For each requirement:

STATUS: DONE / SKIPPED
Evidence or reason skipped

ARTIFACTS
For each required file:

EXISTS: yes / no
SCHEMA COMPLETE: yes / no / partial
Any missing fields listed

LLM CALLS

Total required calls per PRD: X
Total logged in llm_calls.jsonl: Y
Missing call stages listed if any

VALIDATION

Validate.py result: PASSED / FAILED / NOT RUN
Checks passing: X
Checks failing: X
Any failing checks listed

SCOPE CREEP
List anything implemented that was NOT in the PRD.
For each: assess if it helps or hurts the submission.
FINAL VERDICT
One of:

READY TO SUBMIT: all MUST requirements done, validation passing
SUBMIT WITH GAPS: mostly done, list what is missing and whether it is acceptable
DO NOT SUBMIT: critical requirements missing, list what needs to be fixed first

PRIORITY FIX LIST
If not READY TO SUBMIT, list fixes in order of importance:

Fix this first (critical)
Fix this second (major)
Fix this if time allows (minor)


Step 6 — Fix Critical Issues
If the verdict is not READY TO SUBMIT and time allows:
Work through the priority fix list in order. After each fix, re-run validate.py to confirm the check now passes.
Do not add features not in the PRD. Only fix what is missing or broken.