# Idea: Framework dashboard (add any class or subject from an FBISE framework URL)

Status: **idea only, not built** (saved 11 Oct 2026). Part 1 (Class XI, all groups) was
added by hand with the steps below. This idea turns those steps into one guided flow.

## Goal

An admin pastes the URL of an FBISE Assessment Framework (any class, any subject).
NISAAB does every step and stops once for a human to approve the result:

| Step | Today (by hand) | With the dashboard |
|---|---|---|
| 1. Download the PDF | browser / curl | fetched from the pasted URL, kept in Cloud Storage |
| 2. Extract text | pypdf in a script | automatic |
| 3. Parse SLOs (code, description, exam form, K/U/A) | three parsers: `parse_af.py`, `extract_af_llm.py`, `parse_cs_af.py` | one extractor: rule-based first, AI fallback with the existing safety rules (codes must match the PDF, every word must appear in the PDF) |
| 4. Clean and check | `clean_descriptions.py`, compare scripts | automatic; flags missing codes, duplicates, FBISE typos |
| 5. Review | read the JSON file | **diff screen**: new / changed / removed SLOs against what is live, with counts per domain; Approve or Reject |
| 6. Load into the platform | commit JSON, deploy, seed job | on Approve, the SLOs are loaded straight into the database (versioned, with undo) |
| 7. Content | `deploy.sh content`, `--style numerical` | buttons: generate question bank / numericals bank, with progress |
| 8. Check | cloud test | automatic count and sample-question check |

## Honest assessment

- The core pipeline (steps 1–4 and 6–8 as one command) is clearly worth it. Part 2 needs
  4 more subjects, compulsory subjects would add 5, SSC would add many more, and FBISE
  changes frameworks (the 50% pattern in Aug 2026).
- Full automation with no review is NOT worth it: every subject's PDF table looks
  different, and a wrong SLO teaches students the wrong syllabus. The approval step stays.
- The dashboard screen is a nice-to-have. Frameworks change a few times a year, so a
  command is enough for us; the screen matters for teachers/admins and for demos.

## Suggested order

1. Build the one-command pipeline while adding Part 2 (Class XII), so the 4 new
   subjects test it.
2. Add the dashboard (upload URL, diff, approve, generate banks) after the 29 Oct
   competition, or earlier only if Part 2 is finished with time to spare.
3. Admin-only access (the same role as teacher review).
