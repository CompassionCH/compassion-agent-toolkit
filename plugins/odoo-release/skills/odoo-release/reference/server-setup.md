# One-time server setup

Read this when the preflight (phase 2) fails, when the upload folder is not writable, or before the first release on a new server. Everything here is run **by the user, as root, once**; the skill never edits server permissions itself.

## 1. Stop and start the Odoo services without a password (polkit)

A manual `sudo systemctl stop` / `start` in a terminal adds minutes of downtime. A narrow polkit rule lets the deploy user control **only the Odoo units**, with no shell and no other unit. Install it as root, once per server (polkit reloads it by itself; adapt the user and the units):

```js
polkit.addRule(function(action, subject) {
    if (action.id == "org.freedesktop.systemd1.manage-units" &&
        subject.user == "<ssh user>" &&
        ["<service 1>", "<service 2>"].indexOf(action.lookup("unit")) >= 0 &&
        ["start", "stop", "restart"].indexOf(action.lookup("verb")) >= 0) {
        return polkit.Result.YES;
    }
});
```
in `/etc/polkit-1/rules.d/50-odoo-release.rules` (mode 644). It is revoked by deleting the file. Check it with the preflight of phase 2. Do not use `pkcheck --detail`: polkit refuses it for non-root users ("Only trusted callers can pass details") and it always looks like "not allowed".

## 2. The update must log to the file the skill reads

The launcher passes `--logfile` and `--log-level info` on the command line, which overrides the config. **`syslog` still wins over `logfile`** (`odoo/netsvc.py`): `update.conf` must not set `syslog = True`, otherwise nothing reaches the file, the watcher sees no progress and the evaluation finds no `Modules loaded.`.

## 3. The update runs as the SSH user, not as the service user

Files the update writes (attachments created by data files, in the filestore) are owned by the SSH user. The service user must still be able to write next to them. Requirements, to check once per server:
- the SSH user belongs to the service user's group (`id`);
- the data directory and the filestore are group-writable with the `setgid` bit (`drwxrws---`), so new entries keep the service group;
- the launcher runs with `umask 002`, so what the update creates is group-writable.
After a release, an optional check: `find <filestore> -user <ssh user> ! -perm -g+w` must print nothing.

## 4. Upload folder of the release notes

The user needs write access to the folder served by the web server, and nothing else. A dedicated group owns the folder; `setgid` makes new files inherit the group; the web server reads through the "other" permissions:
```bash
sudo groupadd --system releasenotes
sudo usermod -aG releasenotes <upload user>     # effective for the next SSH session
sudo chgrp releasenotes <remote_dir>
sudo chmod 2775 <remote_dir>
```
Do not put the upload user in the web server's own group (it can expose other private folders of the web server). Check it read-only with `ssh <release_notes.ssh> 'id; test -w <remote_dir> && echo writable'`, and with a harmless marker file that you upload and delete at once. The web server must serve the folder as static files (`alias`, no script handler).
