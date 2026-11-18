# ADR format

The default for a repository whose ADR folder has no format of its own.

## Template

```md
# {Short title stating the decision}

{1-3 sentences: the context, what was decided, and why.}
```

That is enough. An ADR can be a single paragraph: its value is recording that a decision was made and why, not filling in sections.

## Optional sections

Add one only when it carries something:

- **Considered options:** the alternatives, when the reason for rejecting them is not obvious. Otherwise someone proposes them again in six months.
- **Consequences:** downstream effects a reader would not guess.

## What qualifies

- **Architectural shape:** how modules split their work, where a flow lives.
- **Integration patterns** between modules or systems: events, bridges, webhooks.
- **Technology choices that carry lock-in:** the ones that would take months to swap out, not every library.
- **Boundary and scope decisions:** what a module owns, what it never depends on. The explicit no-s are as valuable as the yes-s.
- **Deliberate deviations from the obvious path,** so the next person does not "fix" them.
- **Constraints not visible in the code:** compliance, a partner's API contract.
- **Rejected alternatives,** when the rejection is not obvious.

Skip a decision that is easy to reverse (you will just reverse it), unsurprising (nobody will wonder why) or without a real alternative.

---

The ADR skill (`SKILL.md` and this file) is adapted from mattpocock/skills (`skills/engineering/domain-modeling/`, revision c55ee46), distributed under the following licence:

MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
