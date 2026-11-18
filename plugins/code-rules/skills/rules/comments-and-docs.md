# Comments and docs

## Comments describe the code in front of the reader

- **Current code only.** Write for a reader who has the code but not its history: what this code does, and the invariant it upholds. What it replaced, why it changed, the ticket and the migration go in the commit message and the PR.
- **The current reason.** When the reason for a piece of code changes, update its comment even if the code stays: a guard explained by a reason that is no longer true invites someone to delete it.
- **This module only.** The comments of a module others reuse describe that module. They name no module that consumes it and no project phase. A bridge module that exists to join two modules names them.
- **Self-contained contrast.** Mention an alternative only when a reader would otherwise "fix" the code back to it, and say why in the same sentence: "The version is checked, not the column: upgrading the other module creates the column without upgrading this one."
- **Promise only what the code does.** A docstring about a cache that does not cache, or a "never fails" for a path that now fails, is a bug.

The test: forget the previous version and read the comment again. If it no longer makes sense, or answers a question no reader has, rewrite it to describe the code in front of them.

## Docs change with the code

- In the same PR as the behaviour: the comments and docstrings around it, field help texts and user-facing messages, the module's description, and its configuration docs.
- A new setting is explained where the next person looks for it, in the module's configuration docs, not only in the PR description.
- A comment or template header that documents a route, a signature or a parameter changes with it.
- Generated docs: edit their source (the readme fragments) and let the repository's generator rebuild them, locally or after merge as the repository does. Never edit the generated file by hand.
- Known limits and future work go in the module's roadmap section or an issue, not in code comments.
