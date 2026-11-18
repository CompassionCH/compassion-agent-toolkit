# Odoo access control

## Routes and model methods

- Recheck submitted values on the server. Derive the acting partner, amount and other authoritative values from records the caller is entitled to use.
- Before a privileged write, establish which record the caller may change. For example, a visitor changing a checkout partner's email must still have exclusive control of that partner. If someone else may own it, keep their details intact.
- Prefix new internal model helpers with `_`. If an existing method must retain its name and stay internal, use `@api.private`. For methods exposed over RPC, check the caller's authority over the requested records and operation, including work performed with `sudo()`.

## Reviewing ACLs and record rules

Start from each changed ACL or record rule. Identify the affected model, groups and operations (`read`, `write`, `create`, `unlink`), including modes a changed rule stops restricting. Check effective ACL grants across the user's groups. An ACL with an empty group grants its enabled modes to every user.

For each granted mode, inspect the applicable record rules and their domains as that user. A rule with a mode unchecked places no restriction on that operation. Check which records the user can reach, including another user's or company's records where those boundaries apply.

Grant the narrowest group and modes the workflow needs. Use a module role for role-specific work. A read grant for shared reference data can serve a wider group when everyone in it needs that access.
