# Operating Systems Virtual Lab

Development deployment for synthetic accounts: [open the lab](https://br-withered-thunder-bgnp8v2a-oslab.compute.c-9.eu-central-1.aws.neon.tech/). Real enrollment remains closed pending institutional data-protection approval. See the [Student Homework Guide](student-guide.md) and [Instructor Guide](instructor-guide.md).

## Assignment
Individual, English, 14 days from verified release. Five choices: Online Gaming, Smart Security Cameras, Hospital Monitoring, Video Streaming, Autonomous Farm Robot. Students may open any or all of the five cases; each case is a separate attempt that is saved, resumed, submitted and graded on its own. Weight subject to official course assessment plan.

## Workflow
1. Verified login and case selection.
2. Architecture diagram and process/thread design.
3. Personalized CPU scheduling, synchronization/deadlock, virtual memory, file allocation and locking exercises.
4. Save manual predictions before revealing simulation results; preserve original answers immutably.
5. Repeat simulation freely; record corrections and engineering reasoning separately.
6. Local computer experiment: normal vs increased workload; record CPU, memory, disk and thread measurements with screenshots. Clinical and robot scenarios are representative simulations only.
7. Checklist, draft and final reports (unlimited downloads), single final submission unless instructor reopens; PDF uploaded to UBIS.

## Backend requirements
Neon Auth with verified student roster, private PostgreSQL tables, row-level security, instructor role assigned only by trusted administrator, private attachment storage. Never commit student records or service role keys. Server-generated workloads, server-side scoring and atomic answer locking; append-only experiment history; server-enforced deadline and attempt limits. Versioned writes prevent stale tabs overwriting data. Local draft recovery with explicit pending sync indicator; no lock or submission acknowledgement until server confirms. Re-login restores saved state on another device.

## Grading
Architecture 10; process/thread 10; scheduling 15; synchronization/deadlock 15; virtual memory 20; file systems 20; engineering evaluation 10. Automated scoring only for objectively defined items; manual review for design and reasoning.

## Release gates
- Verify institutional approval for external processing of student data.
- Configure auth and roster; test unauthorized cross-student reads/writes and instructor access.
- Test all five workflows, two-attempt permissions, session expiry, cross-device resume, offline recovery, concurrent edits, immutable predictions, deadline, report and attachment export.
- Verify scheduling and replacement results against independent reference examples.
- Verify the Neon Function application URL and browser operation.
- Publish student guide and instructor guide only after tests pass.

## Tests
- Unit: `node --test virtual-lab/engine.test.mjs virtual-lab/drafts.test.mjs` (simulation references, workload variety, draft merging).
- Browser: `node virtual-lab/browser.test.cjs` with `LAB_URL`, `CHROME_PATH`, `LAB_TEST_EMAIL`, `LAB_TEST_PASSWORD` (needs `playwright-core`).
- Live API: `node virtual-lab/live.test.mjs` with `LAB_URL` and `LAB_TEST_ACCOUNTS` (five synthetic students, then one instructor).
- Deploy `drafts.mjs` together with `app.mjs`; the page imports it.
