# Test record

Date: 2026-10-02, Asia/Shanghai. Repository: G:/AI_projects/clashvergedirectrelu.

## Automated checks

- ` .venv/Scripts/python.exe -m unittest discover -s tests -v`: 15 tests passed (0.747s). Input normalization/IDNA/rejection, Windows path boundary, script preservation/idempotence, owned duplicate preservation, apply/reapply/restore, uncertain reload rollback, validation failure, mode/mismatch blocking, persistence, interrupted transaction blocking, loopback HTTP Host/Origin/token protection.
- Live read-only check: Windows production named pipe responds; Mihomo v1.19.31, rule mode, TUN enabled, find-process-mode strict. Disk/runtime both contain 9816 rules. Initial signature comparison exposed IP-CIDR6 API aliasing to IPCIDR; parser corrected before live mutation. Follow-up validation pending.
- During read-only check, 18 current d90.gdl.netease.com download connections reported chains [DIRECT, domestic-sites group], matched existing netease.com rule. Process path unavailable for these connections; this does not prove game match traffic is direct.

## Remaining limits

- Game session connection route remains unverified until NarakaBladepoint.exe traffic is observed. Do not infer gameplay routing from updater downloads.
- Actual Verge subscription renewal/restart is not forced; persistence is verified by inspecting Verge global-script integration and executing the installed script against an unmanaged configuration.

## Live integration progress

- Corrected IPCIDR6 alias and GEOIP country case normalization; generated YAML and all 9816 live rule signatures then matched.
- 09:58:56: real Mihomo config validation and Windows pipe PUT /configs succeeded. Five default DIRECT rules read back in the expected first positions; UI state backend reports persisted=true, effective=true, mode=rule, TUN=true. Backup: data/backups/20261002-095855-b1bb7d5f. This confirms installed rules, not game-session routing.
- Repeated automated suite after alias correction: 15 passed (0.733s); `node --check static/app.js` succeeded.
- Real browser: loaded Chinese page correctly; added https://routing-test.example/path, normalized to routing-test.example, count changed to 6; duplicate add showed error; applied 6 rules successfully; deleted temporary target and count returned to 5. Found stale-rule status edge case after deletion, corrected by checking applied desired list before reporting effective. Browser restore/reapply and final screenshot pending.
- start.ps1 launched hidden server and opened page. Second launch reused single TCP listener on 127.0.0.1:17891, PID 53656 (venv parent PID 53624). No duplicate listener; port conflict behavior remains to be checked.
- New real patch download connections: at least 8 matched the explicit d90-06.gdl.netease.com rule with chains=[DIRECT]. No NarakaBladepoint.exe process connection observed.
- Expanded suite initially failed the Windows port-conflict test: Python HTTPServer default address reuse permitted duplicate binding. Added SO_EXCLUSIVEADDRUSE on Windows and disabled address reuse; follow-up run below required before claiming startup conflict handled.
- Actual apply/reapply preserved all 12 currently selected proxy groups (GET /proxies before/after comparison).
- Full global Script was executed against the original unmanaged config in Node VM; output exactly matched default rules prepended to original 9816 rules (subscription-regeneration simulation). Real Verge subscription update/restart has not been forced.
- Browser restore succeeded and reported unapplied status; subsequent real apply restored five defaults. Final browser reapply reported success, Chinese labels rendered, screenshot saved locally to screenshots/desktop.png.

## Final acceptance results

- Final expanded automated suite: 21 passed (0.827s), including real Windows socket conflict, malformed HTTP request, disabled process recognition, crash recovery, concurrent script changes and stale-rule status.
- Stopped only the verified project app.py listener, then started via wscript.exe start.vbs. New server health returned expected identity; persisted/effective=true, pendingRecovery=false, mode=rule, TUN=true. Attempting another Server on production port 17891 raised OSError; original server remained healthy.
- UTF-8 re-read of all 18 project text files: no U+FFFD and no runs of five question marks. Chinese content is intact. Subsequent edits also use UTF-8 through apply_patch.
- Browser visual review: Chinese content legible, controls visible, status and success message shown, default five targets present. Browser add/delete/duplicate/apply/restore/reapply verified against actual backend and core, not mocked UI.
- Git staged diff check passed. All 18 staged project files were scanned against actual local core secret and full subscription URLs: zero matches; no data/ files staged, no UTF-8 replacement characters or long question-mark runs. Local data/backups and screenshots are ignored.

## 2026-10-02: product title and general-purpose copy

- Browser reloaded the live page: document.title is exactly 手动智能路由; brand is ROUTING / 手动智能路由; hero is 手动选择，智能路由。 Domestic websites and local programs are now described throughout the shared page, connection hints and README.
- UTF-8 re-read confirmed the exact title and no replacement characters or long question-mark runs in changed frontend files. `node --check static/app.js` and `git diff --check` passed.
- Screenshot refreshed at screenshots/desktop.png. This change only edits displayed text and README; routing contracts and persisted targets retain their existing implementation.

## 2026-10-02 10:09:17: explicitly apply Naraka direct rules

- User requested direct installation of the Naraka set. All five targets already existed; reapplied without duplicate targets.
- Actual core validation/reload succeeded. Read back first five /rules entries: DomainSuffix yjwujian.cn, narakathegame.com, d90.gdl.netease.com, d90-06.gdl.netease.com and ProcessPathRegex for G:/Naraka; every proxy is DIRECT. Exact compiled-prefix comparison passed.
- Global-script persistence and live effective state both true; rule mode and enabled TUN retained. Backup: data/backups/20261002-100917-33c04424. Detailed local evidence: data/naraka-apply-verification.json.
- Observed 18 related connections; no NarakaBladepoint.exe process connection. Core reported hits on both a download-domain rule and the directory rule; this is not verification of a gameplay session.

## 2026-10-02 10:14:49: cloudgame direct destination

- User supplied https://cloudgame.ds.163.com/yjwj?utm_source=yjwjfab. Added normalized domain cloudgame.ds.163.com without retaining URL path or tracking query in the rule.
- Actual core validation/reload succeeded with six managed targets. Read back index 5: DomainSuffix cloudgame.ds.163.com, proxy DIRECT. Persisted/effective flags both true; mode=rule and TUN enabled retained.
- Backup: data/backups/20261002-101449-a6095763. Local result: data/cloudgame-apply-verification.json. This confirms rule installation; the remote website response and accessibility were not tested.

## 2026-10-02: one-click BAT lifecycle

- Added start.bat, restart.bat, stop.bat, shared launcher action and Windows process identity checks. Existing cmd/vbs use the same start flow. No backend or core mutation is performed by lifecycle actions.
- Automated suite: 26 tests passed (0.830s), including verified/foreign listener identity, idle stop, health mismatch, and shared existing routing/HTTP regression tests.
- Windows native check found WMI CreationDate truncates FILETIME to microseconds (observed 100ns delta=2). Creation comparison now uses the documented WMI precision while retaining the actual process handle.
- Executed real restart.bat: exit 0, old listener PID replaced, new server healthy. Executed start.bat on the running server: exit 0, same listener PID retained. Executed stop.bat: exit 0, port released, health offline. Second stop.bat when idle: exit 0. Executed start.bat again: exit 0, server healthy and left running.
- Targets and exact Verge generated config/global Script hashes compared before/after: unchanged. Effective/persisted true, rule mode, enabled TUN retained. Evidence saved locally to data/lifecycle-verification.json.
- After tightening identity to the exact script argument (rejecting Python -c with app.py as an unrelated argument), final suite again passed: 26 tests (0.821s). Saved integration assertions passed; live listener still matches project identity and health is online. UTF-8 readback and git diff check passed.
