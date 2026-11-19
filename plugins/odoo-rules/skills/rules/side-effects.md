# Side effects in Odoo transactions

For provider outcomes, retries and staff handoff, follow `failure-handling.md` in `code-rules:rules`.

## Isolate optional writes

Put each independent, best-effort write inside `with self.env.cr.savepoint():`. Catch exceptions outside the block so Odoo rolls the write back. Re-raise `PG_CONCURRENCY_EXCEPTIONS_TO_RETRY` when the request or job runner owns replay. If an optional job runs without retries and needs staff action, use the handoff below. Log the operation and record reference with the traceback. Let required writes fail the transaction.

## Reconcile a payment transaction

When a charge may have gone through, keep the pending transaction's `reference` and any returned `provider_reference`. Match the verified webhook or status response to that record. For repeatable-read checkouts, reuse the submission guard identified in the repository's `AGENTS.md`. Lock and write the order row before checking earlier payments. A competing request whose snapshot predates the first payment's commit then raises a serialization error and can be replayed against the committed payment. Cover a second request that starts before the first commits and attempts payment afterward.

When the retry window expires, put the payer's next step in `state_message`. If the addon moves the transaction out of `pending`, set its unconfirmed marker before changing state. Refusal handlers and the submission guard must read it.

## Hand unresolved work to staff

For an exhausted job that needs staff action, assign a `mail.activity` on the affected business record. The existing payment integration posts the reference in linked documents' chatter. When adding or changing the handoff of an unconfirmed payment, assign the activity with the reference and where to check it before retrying. If no responsible user is configured, post the instructions and missing assignment in chatter.

In a queued job that hands an exhausted operation to staff, write the notice after the failed work's savepoint rolls back. Return the handled result so the notice commits.

## Neutralize outbound integrations on database copies

When an addon introduces live provider credentials or a production callback override, clear them in the addon's `data/neutralize.sql` if the inherited neutralization leaves them in place. Make scheduled calls respect the provider's disabled state. Otherwise a neutralized copy can still contact production or send callbacks there.
