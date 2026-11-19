# Sibling paths

A fix that closes one path to a bug often leaves another open: a second route to the same record, a job that writes the same field, a consumer that reads the state you changed. Find them before review does.

1. **Name the invariant** the change protects, in one sentence a test can check: "a visitor's session never changes the email of a partner someone else may own", "a payment that may still succeed is never offered again".
2. **List the entry points** that read or write that data, in your code and in the framework and modules it builds on:
   - routes and controllers, including those inherited from the framework or another module;
   - public methods, including those callable over RPC;
   - scheduled and queued jobs;
   - flows that move a record to another owner: signup, merge, copy;
   - every reader of a state or flag whose meaning you change;
   - the same entry point running twice at once: two tabs, a double click, a job and a request.

   Search by every name involved: the model or table, the field, the method, the route, the values of the flag.
3. **Close it at the shared choke point** when one exists: a method every entry point goes through. Name the entry points it covers in its docstring. A guard repeated per route misses the next route.
4. **Guard the invariant itself**, not a proxy another path can satisfy: check the version you depend on, not a column another upgrade can create.
5. **Test each distinct behaviour or permission boundary**, not each writer. Entry points that pass through the same choke point share one test, which can loop over them. An entry point with its own logic or its own access rights gets its own test ([tests.md](tests.md)).
6. **Recheck after a fix that touches the invariant.** A fix for one review point can open another path. When a review fix changes code on the invariant's paths, run the invariant's tests again, over the edge inputs of that invariant (empty values, odd spellings, another user, another company), not only the example that failed.
7. **Write the list in the PR description**: the invariant, each entry point, and the test or the reason that covers it.

Done when every entry point on the list is covered by the change or declared out of scope with its reason.
