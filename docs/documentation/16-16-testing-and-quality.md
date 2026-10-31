# 16. Testing and Quality

## 16.1 End-to-end suite

The suite runs against the live deployment, not against fake services, and is run after every deployment. It contains 52 checks and all 52 pass. In order, it:

1. Creates a test user.
2. Uploads and indexes a document.
3. Exercises search and runs the agent.
4. Completes onboarding for all three groups.
5. Checks every syllabus map.
6. Asks the tutor questions in Roman Urdu.
7. Generates and answers quizzes and flashcards.
8. Builds and marks a short paper and a board-pattern paper.
9. Verifies that a choice pair counts once.
10. Checks mastery and the predicted grade.
11. Deletes everything it created.

Two checks exist to catch bugs that were found during development: a syllabus question must never trigger a web search, and a board question must. Before the suite grew to 52 checks it had 40, and it passed all 40 on 27 September 2026.

## 16.2 Measured performance

| Action | Time |
|---|---|
| Numerical quiz from the pre-generated bank | About 4 seconds (it was 202 seconds before) |
| Quiz card from the bank | 3 to 4 seconds |
| Question card (quick questions) | 4 to 5 seconds |
| Tutor reply to a follow-up | About 11 seconds |
| Flashcards written by the AI | 13 to 20 seconds |
| Chapter mind map (from the syllabus) | Instant |
| Topic mind map written by the AI | 10 to 17 seconds |
| Written answer marked | 6 to 8 seconds |
| Practice paper assembled / marked | Under 1 second / 5 to 8 seconds |
| Half examination paper set | About 90 seconds |

Most of these times are from the cloud test on 27 September 2026. The 4-second numerical quiz and the 90-second half paper come from the final system.

## 16.3 Problems found in testing and their fixes

| Problem | Cause | Fix |
|---|---|---|
| "Transport error" on opening the app | Servers were asleep (cold start) | One server kept warm, faster start-up, automatic retries |
| Maths shown as "frac12" and "theta" | The AI wrote formulas in a broken format | Repaired on screen and cleaned before saving; 16 stored items fixed |
| A quiz shown twice in the chat | Card sent without a stable ID | Every card has a stable ID |
| A quiz missing after reopening a chat | An old cached copy of the chat was shown | The chat reloads fresh every time |
| Blank space and a cut-off input box | Hidden formula copies escaped the scroll area | One scroll area and a fixed page height |
| Slow replies with repeated text after a card | A second AI call after every card | The turn ends on the card |
| A follow-up failed after a quiz | A chat-history note read the question count wrongly (found by the automatic test) | Fixed, and the note can no longer break the chat |

## 16.4 Other checks

- Automated tests for the formula-repair code.
- Full type-checking of the web app before every deployment.
- Frontend tests described in section 8.7.
