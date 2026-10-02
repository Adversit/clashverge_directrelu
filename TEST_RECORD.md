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
