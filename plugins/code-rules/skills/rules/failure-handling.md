# Failure handling

Decide every failure path on purpose: what is kept, what is retried, and who finds out. In Odoo, `odoo-rules:rules` (side effects) gives the mechanics: savepoints, pending records, notices to staff, errors to raise again.

## Calls that change something outside

Sort every failure of a call that writes to an outside service into one of two outcomes. Judge the effect a retry would repeat (the charge, the message sent), not only the call. The service's contract and the evidence decide, not the shape of the error:

- **Definite failure:** the service says it refused, or the evidence shows the effect cannot have happened. The request never reached it (connection refused, certificate rejected before sending), or the buyer never reached the payment page the service may have created. Keep any ID the service returned; the caller may retry.
- **Unknown outcome:** anything else. A timeout or a connection lost after sending, a 5xx, or an answer you cannot read may all hide a completed write. Some even carry the ID of what the service created.

For an unknown outcome:

1. Record it as pending or unconfirmed, in the representation the project already uses for that.
2. Keep a second submission blocked while the first may still succeed, and show the status to the user or the staff who follow it.
3. Settle it with the service's own answer: a status query or its notification.
4. When the service has stopped retrying and the record must leave pending, keep it marked unconfirmed, never refused, and hand it to a person with the reference to check before anyone retries.

A client that raises two exception classes of one family is one way to carry the distinction to every caller.

## Isolating work

- **Side tasks never break the main work.** A notification, invitation, badge or status refresh that runs inside a payment, a submission or a page request is wrapped where it is called. Catch its errors there, log them with the traceback and what still works, and go on. Errors the framework retries, such as a concurrent update, are raised again.
- **Required work fails the whole operation.** Catch only what you can handle. An `except` that passes or returns a default, with no log, hides the bug from everyone.
- **Batches:** where each item stands on its own and partial success is valid, give each item its own boundary, so a failing one is logged and the others are kept. An all-or-nothing batch fails as a whole.

## Failures someone must act on

Nobody reads logs or failed background jobs for business events. When a person must act (enter a card again, check a payment, finish a step a job gave up on), put a notice where they work that says what failed, what it means and what to do. When no one is assigned to receive it, say which setting to fill in, and log an error.

## Requests from outside

- Follow the endpoint's protocol. Verify what it requires (a signature, a token) before acting on a request, and parse only what that check needs.
- Answer the way the sender's protocol expects. Refuse with a client error, not a crash, what fails its checks: a missing or bad signature, a body you cannot parse. Acknowledge a message that can never be used, now or later, so the sender stops resending it. Let the sender retry a message that may become usable, such as a reference not committed yet.
- For a notification webhook, log only the reference before verification, and the full payload only at debug level after it. Keep an access token that authorizes a request out of logs.

## The user's side

Every failure path of a user action ends in a state the user can see. After a definite failure, show the message and enable the action again. After an unknown outcome, show the status and keep the action blocked. When your extension of a third-party widget fails, fall back to the widget as it was.
