# Judging demo script: FSc Tutor (Sunday 5 October 2026)

About 8 minutes live, then questions. Everything runs on the live Google Cloud app:
https://nisaab.muhammadsaadcheema.com

## Before the demo

| When | What |
|---|---|
| 3 Oct | Full rehearsal with this script, on a phone and a laptop. Record a backup video of the whole flow. |
| 3 Oct | Run the cloud check: `deploy/gcp/deploy.sh e2e` (all stages must pass). |
| 4 Oct | Demo mode: in `deploy/gcp/deploy.env` set `WORKER_ALWAYS_ON=true` and `API_MIN_INSTANCES=1`, then `deploy/gcp/deploy.sh deploy --skip-build`. Turn it off after the demo (costs a few dollars a day). |
| 4 Oct | Prepare two accounts (sign up in the app yourself): a **fresh** one for the onboarding step, and a **practised** one that already has 3 to 4 Mechanics SLOs practised, so the dashboard shows a predicted grade and weak SLOs. |
| 4 Oct | Check that Mechanics content is approved by the Physics teacher (Review content page), so practice opens instantly with teacher-checked questions. |
| Demo day | Open the app 10 minutes early on both accounts (warms up the servers). Have the backup video ready. |

## The story (one line)

> An FSc student in Islamabad follows the official FBISE syllabus, SLO by SLO: the tutor explains in their language,
> practice targets exactly what is examined, written answers are marked like a board examiner, and the dashboard shows
> where they stand on the new IBCC grading scale.

## Script

1. **Problem (30 s).** FBISE moved to SLO-based papers (NCP 2022-23) and a new 10-band IBCC grading scale with a 40% pass
   mark. Students still revise from generic material, and nobody tells them which SLOs are examined.

2. **Sign up and onboarding (45 s), fresh account.** Sign up → choose Class XI → Pre-Medical → Roman Urdu.
   Show that Physics XI, Chemistry XI and Biology XI workspaces appear on "My FSc".

3. **Syllabus map (60 s).** Open Physics XI. Show the 7 domains and 193 SLOs taken from the official FBISE Assessment
   Framework (link at the top). Filter "Examined" vs "Not examined" and search "projectile". Point out the K/U/A levels.
   Mention that Chemistry, Biology and Maths maps are there too.

4. **Tutor in Roman Urdu (90 s).** Open SLO P-11-B-05 → "Explain this SLO", or start a chat and type
   *projectile ki range kaise nikalte hain?* The answer is in Roman Urdu, formulas are rendered, and it cites
   SLO P-11-B-05 and exam tips.

5. **Practice by SLO (60 s).** Back in the SLO panel → "Practise 10 MCQs". Teacher-reviewed questions open instantly;
   answer two or three. Show the explanation with the worked formula.

6. **Written answer marked like an examiner (90 s).** "Written answer (SRQ), marked by AI". Type a half-right answer
   (e.g. correct formula, wrong arithmetic, missing unit). Submit: marks per rubric point, what was missed, feedback in
   Roman Urdu and a model answer, in a few seconds. Say clearly: "AI-estimated marks".

7. **Progress and predicted grade (45 s), practised account.** "My FSc" → My progress: predicted IBCC grade band
   with its coverage, mastery by domain, and the weakest SLOs with a Practise link. Practise one weak SLO and come back:
   the numbers move.

8. **Quality and trust (30 s).** Content is generated ahead of time and checked by a Physics teacher on the Review page
   (approve / reject with a note); students never see rejected items. Notice in the footer: aligned with FBISE NCP 2022-23,
   not an official FBISE product.

9. **Close (20 s).** Built on Google Cloud (Cloud Run, Vertex AI Gemini, Cloud SQL, Identity Platform). Next: Class XII,
   full mock papers on both FBISE patterns, teacher dashboards.

## If something goes wrong

- A generated item takes long: say it is being written live, and use an SLO whose content is already in the bank
  (Mechanics).
- The AI is slow or rate-limited: the models fall back automatically; if the page still hangs, switch to the backup video
  for that step and continue live afterwards.
- Sign-up problem: use the prepared fresh account and skip to onboarding.

## Likely questions

- **Is the syllabus data official?** Parsed from FBISE's published Assessment Frameworks; every SLO code matches the PDF.
  Chemistry, Biology and Maths maps still need a teacher's spot check.
- **Can AI marks be trusted?** They are labelled as estimates, marked point by point against a rubric at temperature 0;
  the next step is calibrating against teacher-marked answers.
- **Data and privacy?** Student data stays in our Google Cloud project; the paid Vertex AI API does not train on it.
- **Cost per student?** Most practice uses pre-generated, reviewed content; live AI is used for the tutor and marking.
