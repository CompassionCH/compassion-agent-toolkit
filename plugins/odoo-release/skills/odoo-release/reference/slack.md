# Slack messages

Written to `$WORK/slack-message*.txt` and **shown in the chat in a code block**, ready to copy-paste. The skill never posts to Slack. In `release_notes.language`, 3 to 5 lines, no module or technical names. Slack formatting: `*bold*` and `:emoji:` (both are converted by the composer). **The link is the plain URL, on its own, with nothing around it**: never `<url|text>`, `<url>` or a Markdown link. The `<url|text>` syntax belongs to Slack's API and webhooks; pasted into the composer it stays literal, so the `|text>` part becomes part of the link and the URL is invalid. Slack links a plain URL by itself. If the composer shows literal asterisks around the title, the user removes them. Start with `slack.mention` when it is set. The link is `release_notes.url_base` + the file name; if `url_base` is not configured, ask the user once for the public URL of the folder and store it.

Times and dates are in `deferral.timezone`. Stage: no Slack message (there are no user release notes).

## Upcoming (deferred deployment, update mode)
```
:wrench: *Odoo update planned*
Odoo will be unavailable on <weekday date> from <HH:MM> for about <N> minutes. Please save your work before.
What changes: <release notes URL, plain>
```

## Running (immediate deployment, update mode)
Give it to the user when the deployment starts, and for a deferred one again when it resumes.
```
:rotating_light: *Odoo update in progress*
Odoo is unavailable for about <N> minutes (started <HH:MM>). Please do not save anything for now, we will say when it is back.
What changes: <release notes URL, plain>
```

## Back online (after an update)
With the **real** downtime, never the estimate.
```
:white_check_mark: *Odoo is back*
The update is done: Odoo was unavailable for about <N> minutes today (<HH:MM> to <HH:MM>). Everything works again, thank you for your patience.
What changes: <release notes URL, plain>
```

## Restart mode (no module to update)
No downtime information, as in the release notes. Sent once the deployment is done:
```
:new: *New Odoo release*
What changes: <release notes URL, plain>
```
