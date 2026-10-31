# 17. Operations Guide

## 17.1 Demo-day checklist

Services are normally switched off between tests to save credits, so a demonstration needs preparation.

| When | Do this |
|---|---|
| A few days before | Bring the services up. Run the end-to-end suite and make sure all 52 checks pass. Confirm the numbers you will quote (869 outcomes, 611 examined, per-subject counts and the size of the bank) against the live system. |
| The day before | Rehearse the demo in the exact order of the deck. Record a video of that run as a backup. Keep the deck as a PDF on a USB stick, with the video on both the laptop and the stick. |
| On the day, before judging | Switch the worker to its always-on mode so papers and generation are not delayed. Open the app once and check sign-in works from the venue network. |
| During the demo | If the internet fails, play the backup video and keep talking. Do not try to fix the connection in front of the judges. |
| After the event | Switch the always-on mode off and shut the services down again to save credits. |

## 17.2 The rehearsed demo order

1. Open a subject and show the syllabus map with domains and outcome codes.
2. Tap one outcome and show the explainer.
3. In the tutor, ask in Roman Urdu: *"projectile ki range kaise nikalte hain?"* and point out the SLO code and the formula.
4. Ask: *"is par 5 numericals do"* and show the quiz appearing in seconds.
5. Answer two questions, one right and one wrong, and show the explanation.
6. Open a half board paper and show a stimulus set and an (a) OR (b) question.
7. Show the progress screen with mastery per outcome and the predicted grade.

## 17.3 Maintenance procedures

**Add a new subject.** Follow the seven stages in section 13. Download the framework, extract and parse it (choose or write the parser that fits its table), check it against FBISE's newest documents, run the seed, generate the practice material, then run the end-to-end suite. Because prompts and tools are written per subject by variables, no new prompt template is needed.

**FBISE changes the paper pattern.** Edit the blueprint table in section 12.1, re-parse and re-seed any framework that changed, regenerate any affected material and run the suite. This is how the August 2026 change was handled within a week.

**Review generated content.** A teacher listed as a reviewer opens the Review content page and approves or rejects each item with a note. Approved items get the "Teacher-checked" badge. Rejected items are hidden from students.

**Remove a student's data.** Deleting the account deletes its projects, documents and document segments through cascading deletes.

**Check that nothing has broken.** Run the end-to-end job after every deployment and compare it with the 52 expected checks.

## 17.4 Keeping costs down

- Use the pre-generated bank for practice so most requests need no model call.
- Let the worker scale to zero when idle, and use always-on mode only for demo days.
- Shut the services down between demonstrations.
- Watch the budget alerts and check real billing before quoting a monthly cost.
