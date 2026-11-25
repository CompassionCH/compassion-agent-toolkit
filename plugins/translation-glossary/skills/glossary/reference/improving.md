# Improving the glossary by pull request

The glossary improves itself: an agent that learns something the references lack opens a pull request on `CompassionCH/compassion-agent-toolkit`, and the maintainers merge it after the communication team's review.

Done when the user has the pull request's link, has the change as text for a maintainer, or has declined it.

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

Show everything that will be published: the file and the lines as they would read, the pull request's title and description, and the branch name. Say that the pull request is public and appears under their GitHub account. Ask before opening it. A decline ends here.

## 4. Open the pull request

This needs `git` and `gh` logged in to GitHub (`gh auth status`). Where they are missing, as in the desktop app's chat, give the user the change as text for a toolkit maintainer, and stop.

`<dir>` below is the clone's folder, written out in full in every command: a shell variable does not survive from one command to the next, and an empty path would make git act on the user's own project.

1. Clone `main` into a new temporary folder, never the installed plugin's files:
   `d="$(mktemp -d)/toolkit" && git clone -q --depth 1 https://github.com/CompassionCH/compassion-agent-toolkit.git "$d" && echo "$d"`
   The printed path is `<dir>`.
2. Create a branch: `git -C <dir> switch -c glossary-<language>-<topic>`.
3. Edit the reference under `plugins/translation-glossary/skills/glossary/reference/`, in the section where the term belongs, in that file's table shape. A new language gets its own file, a row in the table of `SKILL.md`, its name in the `description` of `SKILL.md`, and its name in the README's "Glossaries ship for" sentence.
4. Bump the patch version in `plugins/translation-glossary/.claude-plugin/plugin.json` (`1.2.3` becomes `1.2.4`).
5. Commit everything, new files included: `git -C <dir> add -A && git -C <dir> commit -m "translation-glossary: <language>: <what>" -m "<why>"`.
6. Push the branch. Check the user's access: `gh repo view CompassionCH/compassion-agent-toolkit --json viewerPermission --jq .viewerPermission`.
   - `ADMIN`, `MAINTAIN` or `WRITE`: `git -C <dir> push -u origin <branch>`. `<owner>` is `CompassionCH`.
   - Anything else: `cd <dir> && gh repo fork --remote`, which makes the user's fork `origin` (and the original `upstream`), then `git -C <dir> push -u origin <branch>`. `<owner>` is the user's login: `gh api user --jq .login`.
   - When the push asks for credentials, run `gh auth setup-git` once and push again.
7. Write the description to a file outside `<dir>`: the change, who decided it (by role), and the kind of text it came from ("a newsletter", "the portal's signup form"). Then:
   `cd <dir> && gh pr create --repo CompassionCH/compassion-agent-toolkit --base main --head <owner>:<branch> --title "translation-glossary: <language>: <what>" --body-file <file>`
8. Give the user the link, and delete the temporary folder and the description file.

One point per pull request, so the reviewers can accept or reject each on its own.
