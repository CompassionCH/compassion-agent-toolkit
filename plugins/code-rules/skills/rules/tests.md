# Tests

A test protects the code only if it can fail and someone runs it. The repository's `AGENTS.md` says what its CI runs; assume the tests run only where you run them.

## A test that can fail

- **Red first.** For a fix or a behaviour change, run the new test against the code without your change and watch it fail for the reason you expect. A test that also passes on the base branch does not tell old code from new. A characterization test of existing behaviour may pass on both; say that it is one.
- **The boundary under test.** Drive the code the way it is reached: post to the route or the webhook, call the public method, run the job, as the user who would. Prerequisites the test is not about may be set up directly (a pending payment whose status page you test). The state under test is reached through the code under test, never written by hand: a test of the helper behind the entry point skips the lookups, checks and access rights in front of it.
- **Exact outcome.** Assert the value you expect, not "anything but the old value": a wrong 0 passes a "not 15" check. Assert what proves your code ran: the status code or redirect (a request refused before your code runs still leaves "nothing changed" true), and the content (an error placeholder can come back with a 200).
- **Distinct values.** Give each source of a value its own data (each company, user or website), so a value read from the wrong one shows.
- **Behaviour, not markup.** An attribute in the rendered page proves nothing about what the server accepts. Send the bad input and assert the refusal.

## Self-contained

- **Own fixtures.** The setup creates, or switches on, every record the test relies on: an available item, an active currency, a configured provider, the responsible user. A test that needs the database to already hold them fails on an empty one and passes by luck on a copy.
- **Own scope.** Search and count only the test's own records, or compare a count before and after. A global search with an exact count breaks on any database that holds similar data.
- **Deterministic.** Seed any randomness at the test boundary and restore it afterwards (`addCleanup`), so nothing leaks into other tests.
- **Mock the next boundary out.** Testing your client: fake its transport. Testing code that uses your client: patch the client, not the internals of a third-party library. A fake of someone else's shape only tests your guess of it.
- **Expected errors are captured.** A test that triggers an error log captures that logger by name (`assertLogs`, or the framework's helper), so an unexpected error still shows.

## What to cover

- The paths that cost money or data when they go wrong: the refusal, the unknown or pending outcome, the retry, two requests at once. Not only the final states.
- The user the code serves: a visitor, a user of another company or website, not the administrator running the test. When the code notifies or assigns someone, make that someone a different user from the one acting.
- Each bug found in review, with the edge inputs that broke it.
- Every entry point to the same invariant: see [sibling-paths.md](sibling-paths.md).

## Run and report

Run the tests that exercise the behaviour you changed, and any wider suite the repository's `AGENTS.md` asks for. When a test fails that you did not touch, run it on the base branch and report it as existing if it fails there too. Report the commands, the results and the environment they ran in, described generically ("an empty database", "a copy of production data"), in the PR description ([pr-hygiene.md](pr-hygiene.md)).
