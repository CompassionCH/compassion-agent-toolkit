# Pull requests

PR text and replies to review are drafts for the user. Post them only where you were asked to publish.

## Scope

- **A focused diff.** Commit only what the subject needs. Leave out reformatting, drive-by cleanups, an edited dependency list, a moved line. A separate fix gets its own PR, unless an ADR of the repository asks for it with this change; then name it in the description. Changes in the working tree that are not yours stay untouched: leave them out of your commits, never discard them.
- **Conflicts:** resolve each by the behaviour both sides intend, often by keeping both.
- **Before pushing,** run the checks the repository's CI runs, with the commands in its `AGENTS.md`.

## Description

Keep it true to the last commit: reviewers and the next maintainer read it, not the history of the branch. After every review round, update what changed. It holds, when they apply:

- **What and why:** the problem and the change, in terms of behaviour, in plain words that a reader without access to the ticket understands.
- **Decisions** taken along the way, with the role that confirmed each one.
- **Companion PRs** as `owner/repo#number`, the merge order, and what breaks when only one is deployed. Where a wrong order would break a deployment, add a check that stops it with a message naming what to run.
- **Deployment notes,** when deploying needs more than a merge: the exact upgrade command with everything that must be upgraded together, the settings to fill in, the data to check.
- **How to test:** steps a reviewer can follow.
- **Test evidence** ([tests.md](tests.md)): commands, results, the environment described generically, which tests were red without the change, and which failures also happen on the base branch.
- **Sibling paths** ([sibling-paths.md](sibling-paths.md)): the invariant, its entry points and what covers each.
- **Rules review** ([review.md](review.md)): each finding and coverage gap, and what you did about it.

## Evidence

- **Say how you know:** run, read, or assumed. "Traced in the code, not run" is a fine answer; a claimed run that did not happen is not.
- **Correct in the open.** When a claim in the description or a reply turns out wrong, draft a correction that says what was wrong.

## Answering review

Draft the answers for the user. The answers that settled threads named the commit that fixes it and, for a behaviour change, the test that fails without the fix, or gave the reason for disagreeing.
