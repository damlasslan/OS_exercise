# Instructor Guide

## Development access

Use synthetic identities ending in @example.invalid. The API enforces this restriction on every session lookup. Keep institutional enrollment closed pending data-protection approval. Never commit credentials, screenshots, rosters or exported submissions.

A trusted administrator provisions verified Neon Auth identities and links each synthetic student's auth UUID and exact email to lab.roster. Add only authorized instructor UUIDs to lab.instructors. Credentials belong in private credential storage. The synthetic assignment runs for 14 days from creation. Check opens_at and closes_at in lab.assignments before starting an exercise.

## Review workflow

Sign in and open **Instructor dashboard**. Choose a student's attempt to review the workload, original numeric predictions, corrected explanations, diagram and measurement screenshots. A missing submission timestamp means the attempt is still a draft.

The server awards up to 60 points for the initial predictions: Round Robin average waiting 15, synchronized-resource exercise 10, LRU faults 20 and data block count 15. For the remaining 40, evaluate architecture (10), process/thread design (10), deadlock reasoning (5), file locking and allocation reasoning (5), and engineering evaluation (10). Enter the manual score and written feedback, then save. These weights implement the seven published categories.

Students may open all five cases; each case is a separate attempt with its own submission and grade, listed separately on the dashboard. Use **Reopen submitted attempt** for a revision during the open assignment window. Reopening preserves original predictions and archived final snapshots. The next submission requires a new manual evaluation.

## Deployment and tests

The Node 24 Neon Function runs on the existing development branch. Run multi-case.sql once on the development database. Archive index.mjs, app.mjs, index.html, engine.mjs, drafts.mjs and preview.html at the ZIP root. Deploy the oslab function to development only. DATABASE_URL is provided by the branch. The checked-in handler uses this branch's public Neon Auth endpoint. Run engine.test.mjs with node --test. Run draft-api.test.sql only on the development database; it rolls back its synthetic fixtures. The live integration test requires six dedicated synthetic credential pairs in LAB_TEST_ACCOUNTS (JSON array, five students followed by one instructor) and LAB_URL. It creates actual submissions on those synthetic accounts.
