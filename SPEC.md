# Clash Verge Direct Manager

Date: 2026-10-02 (Asia/Shanghai)

## Product and ownership

Local Windows web app for observing Naraka routing and managing explicit DIRECT destinations. `data/targets.json` owns the manager's targets. The existing Clash Verge subscription, mode, TUN, DNS, proxies and selections remain owned by Clash Verge. The app projects only its managed rules into the global Script profile and the current runtime configuration. No mailbox files change.

## Two-pass inspection

Pass 1: Browser -> loopback HTTP API -> target store -> rule compiler -> Verge global Script -> Mihomo runtime API. Current installation: D:/clash verge; data: %APPDATA%/io.github.clash-verge-rev.clash-verge-rev; rule mode, system proxy and TUN enabled. Game currently stopped.

Pass 2: Inspect profiles.yaml, global Merge/Script, current subscription merge/script/rules, generated clash-verge.yaml, config.yaml, verge.yaml, logs and Naraka launcher/update logs. Current global and subscription scripts are identity functions; no managed rules exist. Runtime HTTP controller is disabled; a Windows named pipe is configured. Do not expose a new controller or its secret to the browser. Preserve subscription credentials and existing rules.

## Contracts

- GET /api/state: UTF-8 JSON with targets, online/mode/TUN, observed related connections, installed executable inventory and last apply result. No credentials or raw subscription content.
- POST /api/targets: {kind: domain|folder, value: string, label: string}; normalize full HTTP(S) URLs into hostnames and IDNA; reject empty/invalid/injected input. Directory must exist and compile into an anchored case-insensitive Windows PROCESS-PATH-REGEX.
- DELETE /api/targets/<id>: remove only manager-owned target.
- POST /api/apply: project all saved targets, validate with installed Mihomo, reload current rules and verify /rules. Report persisted versus effective separately; never silently switch global/TUN settings.
- POST /api/restore: remove managed global-script block and managed runtime rules, preserving current unrelated rules. Backups and transaction status stay local.
- Changes require same-origin JSON requests and a session token. Listen on 127.0.0.1 only, validate Host/Origin, never send controller secrets to clients.

## Files changing together

Within this folder: app.py (server/transport), manager.py (store/compiler/Verge adapter), static/index.html, static/app.js, static/style.css, start.cmd, start.ps1, requirements.txt, README.md, tests/, TEST_RECORD.md, DETECTION_REPORT.md, data/targets.json. External files: global profiles/Script.js and generated clash-verge.yaml, only upon apply/restore, with timestamped backups. profiles.yaml/verge.yaml/config.yaml and subscription source files are read only.

## Old-logic removal

No prior implementation to migrate. On reapply remove the previous managed script block and previous managed rule projection before adding its replacement. Never append after MATCH; never use obsolete prepend-rules in global Merge. No broad 163.com/netease.com direct rule; scope to observed game hosts and directory. Do not auto-close unrelated connections or launch the game.

## Acceptance checklist

- [x] Detect mode/TUN/controller and actual related connections, separating no observations from DIRECT evidence.
- [x] Seed verified official domains and hosts observed in local game update logs, with provenance.
- [x] Cover G:/Naraka and descendants with anchored path rules; exclude G:/NarakaOther (compiler test; gameplay pending).
- [x] Add/delete host targets, persist across restart, explicitly apply, verify rule order and readback.
- [x] Preserve unrelated script/config/rules; subscription regeneration retains targets via global script (simulation; actual Verge subscription renewal pending).
- [x] Named-pipe runtime API works without opening another controller listener.
- [x] Validate configuration before reload; retain/restore on validation or reload failure (fault tests plus actual restore).
- [x] One-click hidden server startup, repeated startup reuses its own live server, useful missing-runtime/offline errors (startup/conflict verified; missing runtime branch inspected).
- [x] Real browser functional/visual verification and test results recorded in TEST_RECORD.md.

## Failure branches

Empty/short URL, paths/credentials in URL, duplicate hostname, IDNA, IP input, commas/newlines, missing folder, regex escaping, case and separator normalization, unrelated path boundary; malformed store; unsupported/missing core; disconnected pipe; pipe permission error; startup race/port conflict; config changed concurrently; global script missing main or conflicting markers; global mode (rules ineffective) and TUN off (game may bypass core); no live game; existing connections retain route until reconnected; reload or readback mismatch; backup rollback; manager shutdown (global script persists).

## Validation and reporting

Focused tests must cover input, ownership, transactions and runtime readback. Write every executed result to TEST_RECORD.md before claiming it passed. A running game's actual DIRECT route is pending unless observed; static config validity never proves in-game behavior.

## Implementation contract supplement

- Runtime reload uses PUT /configs with UTF-8 YAML `payload`, not a file path inaccessible to the Windows service. Snapshot /rules must match generated YAML before mutation; preserve current runtime mode, TUN and selected proxies.
- Domains compile to DOMAIN-SUFFIX (host plus subdomains); default targets: yjwujian.cn, narakathegame.com, d90.gdl.netease.com, d90-06.gdl.netease.com, and G:/Naraka. Shared account/telemetry domains in tool logs are not evidence of game-specific destinations.
- Store schema 1: targets {id,kind,value,label,source}; applied.json tracks inserted rules and last result. Only the exact manager-owned leading rule sequence is removed, preserving preexisting identical rules.
- Script projection appends a marked wrapper around the original main function; restoring strips only that block. Global Script file resolved from profiles.yaml. Node validates/evaluates the wrapper before any external write. Process recognition is left unchanged; directory apply refuses find-process-mode=off.
- data/backups holds original config/script and a transaction journal; failed reload/readback attempts rollback, with explicit recovery-required status if rollback cannot be confirmed. Pending crash journals block new apply until recovery (POST /api/recover).
- Additional affected files: launcher.py, start.vbs, tests/test_manager.py, tests/test_http.py. start.vbs launches hidden; launcher holds a Windows mutex, installs pinned dependency when missing, checks server identity and opens the page. Port conflicts never terminate other processes.
- No deletion of the old mailbox checkout is required: existing partial files already reside in the requested independent directory.

## Lifecycle scripts contract (2026-10-02)

1. Ownership: Windows listener at 127.0.0.1:17891 owns running status; all lifecycle actions share the existing launcher mutex. Rules and target data retain their existing owners.
2. Input/output: start.bat / restart.bat / stop.bat -> start.ps1 -Action start|restart|stop -> launcher.py --action. Launcher returns 0 on success; visible error dialog and nonzero on unsafe process identity or startup failure. PowerShell waits for the launcher process only, not its persistent server child.
3. Affected files: launcher.py, start.ps1, start.bat, restart.bat, stop.bat, tests/test_launcher.py, README.md, SPEC.md, TEST_RECORD.md. Backend HTTP contract, store schemas and Verge adapter do not change.
4. Removal: replace start-only main flow with a shared locked lifecycle flow. Retain start.cmd/start.vbs compatibility; no broad taskkill or process-name termination paths.
5. Acceptance: restart replaces the old listener and returns a healthy page; stop releases the port; stopping when idle succeeds; repeated start reuses the same listener. Existing targets, persisted DIRECT rules, mode and TUN remain unchanged.
6. Failure branches: missing Python, occupied port, unrelated listener, mismatched app path, vanished/reused PID, simultaneous operations and startup timeout. Termination requires expected health identity, exact absolute app.py argument, Python executable and matching Windows creation FILETIME at WMI microsecond precision on a retained process handle. Refuse ambiguous processes. Serialize actions with the launcher mutex.

Review pass 1: entry BAT -> PowerShell -> launcher -> loopback listener. Review pass 2: inspect default venv parent/base Python child, runtime process identity, original cmd/vbs startup, state persistence and core rules; stopping the website must not call core reload/restore.
