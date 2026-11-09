> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 14. Security and Privacy

## 14.1 Authentication

Google Identity Platform issues ID tokens to the browser. The API verifies each token against Google's published JSON Web Key Set, checking the signature, issuer, audience and expiry. Signing keys are cached for an hour. No password reaches the application.

## 14.2 Authorisation

Every query is limited by owner. Retrieval over uploaded documents first resolves the project's own document identifiers and restricts the vector search to them. The user endpoints were tightened during development so that a signed-in student can read or delete only their own account.

## 14.3 Secrets and network

- No credential is kept in the repository. The database connection string and API keys live in Google Secret Manager and are mounted into the services as environment variables.
- The service account holds only the roles it needs.
- The database has no public address. Cloud Run services reach it over a private Unix socket.
- The worker is private and is called only by Cloud Scheduler.

## 14.4 Student data

- Uploaded files are stored in Cloud Storage. Extracted text and its embeddings are stored in the database, limited to the project.
- Foreign keys cascade on delete, so removing an account removes its documents and segments.
- Student uploads never enter the shared question bank.
- Only the personal data needed for sign-in is collected. The paid Vertex AI service does not use project data for training.
- Many users are 16 to 18 years old, so consent and a privacy policy are planned before any wider beta.
