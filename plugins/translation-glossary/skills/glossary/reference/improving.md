# Improving the glossary by pull request

The glossary improves itself: an agent that learns something the references lack opens a pull request on `CompassionCH/compassion-agent-toolkit`, and the maintainers merge it after the communication team's review.

Done when the user has the pull request's link, or has declined it.

## 1. Check that it qualifies

Open a pull request for a **settled** point only:

- a term the reference lacked, and the user or a reviewer decided it;
- a correction a reviewer made to the wording, which the reference would have prevented;
- a contradiction between the reference and approved material, with the version the user confirmed;
- a new language's glossary, once the user approved it (`new-language.md`).

Your own unconfirmed preference stays out: name it to the user instead.

## 2. Keep personal data out

The pull request is public. Write the English term, the agreed term and the reason, with generic examples only. Leave out supporters' and children's names, letter or email content, ticket numbers and anything else from the text you were translating. Name who decided by role ("the communication team", "a native reviewer"), not by name.

## 3. Ask the user

Show the change: the file, the lines as they would read, and the reason. Ask before opening the pull request. A decline ends here.

## 4. Open the pull request

This needs `git` and `gh` logged in to GitHub (`gh auth status`). Where they are missing, as in the desktop app's chat, give the user the change as text for a toolkit maintainer, and stop.

1. Clone `main` into a new temporary folder, never the installed plugin's files:
   `d="$(mktemp -d)" && git clone -q --depth 1 https://github.com/CompassionCH/compassion-agent-toolkit.git "$d" && echo "$d"`
2. Create a branch: `git -C "$d" switch -c glossary-<language>-<topic>`.
3. Edit the reference under `plugins/translation-glossary/skills/glossary/reference/`, in the section where the term belongs, in that file's table shape. A new language gets its own file, a row in the table of `SKILL.md`, and its name in the `description` of `SKILL.md`.
4. Bump the patch version in `plugins/translation-glossary/.claude-plugin/plugin.json` (`1.2.3` becomes `1.2.4`).
5. Commit with a message that says what changed and why.
6. Push the branch. Without write access to the repository, fork it first: `gh repo fork --remote` in `"$d"`, then push to the fork.
7. `gh pr create --repo CompassionCH/compassion-agent-toolkit`, titled `translation-glossary: <language>: <what>`. The body gives the change, who decided it (by role), and the kind of text it came from ("a newsletter", "the portal's signup form").
8. Give the user the link, and delete the temporary folder.

One point per pull request, so the reviewers can accept or reject each on its own.
