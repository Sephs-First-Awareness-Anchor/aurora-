# Aurora Strata Link — Setup and Operation

**Authors:** Sunni (Sir) Morningstar & Cael Devo
**Added:** 2026-11-11 (FIX-A118) · Module: `aurora_internal/dual_strata/strata_link.py`

The strata link carries Aurora's existing surface/subsurface channels between
the phone (Surface) and the Windows laptop (Subsurface). It contains no
cognition and adds no new channel formats.

## What crosses today

| Direction | Channel | Notes |
|---|---|---|
| phone → laptop | continuity feed (one packet per lived turn) | on as soon as paired |
| phone → laptop | sensory snapshot (latest wins, sent only when it changed; over 1.5 MB is not sent) | on as soon as paired |
| laptop → phone | subsurface projection, predictive frames, sensory guidance | **off until seeded** (see "Seeding") |
| either way, on request | whole-state transfer: **seed** and **handoff** | see "Seeding" and "Moving the Surface to another device" |

Turn events and the presence frame stay on the phone on purpose: that loop is
latency-critical and the phone already runs it locally. The phone keeps her
full local cognition, so losing the link never blocks a reply.

## State ownership

| State | Owner | Other side holds |
|---|---|---|
| A lived turn's continuity packet | the Surface that lived it, until acknowledged | — |
| Integrated continuity (SediMemory etc.) | Subsurface | — |
| Active-surface record and epoch (`strata_link/server_state.json`) | Subsurface | Surface is told its role each sync |
| Projection, predictive frames | Subsurface | Surface holds a delivered copy |
| Uplink outbox (`strata_link/up_outbox.json`) | Surface | — |
| Downlink outbox (`strata_link/down_outbox.json`) | Subsurface | — |

Only the owning Surface's records are applied. A second device is told
`standby` and its outbox waits. Ownership moves only by an explicit claim
(pairing is one), which raises the epoch.

## Reaching the laptop from anywhere

The phone always dials the laptop. Away from home Wi-Fi the phone needs a
private route to it. The link itself only needs a hostname the phone can
reach; a private mesh network such as Tailscale (Windows and Android clients,
free personal plan) supplies one without opening any port on a router. Every
request and response is also signed with the pairing secret, so the tunnel is
not the only lock.

## Laptop (once)

1. Install Python and the repo's `requirements-core.txt`; put the repo where it will live.
2. Create the pairing line. `--host` is the name or address the phone will dial
   (the laptop's tunnel name, or its Wi-Fi address for a home-only test):

       python -m aurora_internal.dual_strata.strata_link pair --host <laptop-name>

   It prints `http://<laptop-name>:8791#<secret>`. Running `pair` is what marks
   this machine as the Subsurface host; the daemon starts the link from then on.
3. Allow inbound TCP 8791 for Python in Windows Firewall (private networks).
4. Start the Subsurface so it runs with no window and restarts itself:

       powershell -ExecutionPolicy Bypass -File scripts\windows\install_subsurface_task.ps1

   Log: `aurora_state\strata_stack\logs\subsurface.log`.

## Phone (once)

Hub → **Subsurface link** row → tap → paste the pairing line → Pair.
The row then shows `online · N up · M down · rtt`, or `offline` with the reason
and how many turns are waiting.

## Seeding the laptop (once, before the downlink)

A projection only means something when it comes from a Subsurface that has
lived the same history as the Surface it colours. The phone is the one that has
lived it, so the phone gives the laptop its continuity:

    python -m aurora_internal.dual_strata.strata_link seed --state-dir <phone state dir>

(In the app: the bridge call `strata_link_transfer("seed")`; there is no Hub
button for it yet.) What happens:

1. The phone flushes every lived turn to the laptop first, so the transfer
   follows its own history.
2. It snapshots its state files and hashes the *copies*, so the hashes describe
   exactly the bytes sent.
3. The laptop reports which files it already holds byte-for-byte; those are not
   sent. The rest go in 1 MiB chunks, each file verified against its SHA-256
   before it is trusted.
4. Only when every file verifies does the laptop install them. A file it
   replaces is first copied to `strata_link\backup\<transfer id>\`. Files the
   laptop has that the phone does not are left alone.
5. The laptop writes `strata_link\seeded.json` and creates
   `strata_link\downlink_enabled` — the stated condition for the downlink is
   now met and verified.

An interrupted transfer resumes where it stopped (the transfer id is derived
from the content). **Restart the laptop daemon after a seed:** it holds her
state in memory and does not re-read the files it just received;
`seeded.json` says `restart_required`.

Not transferred: the link's own folder (secrets, outboxes, device identity),
live channel files the link already carries, per-device heartbeats/status/
locks, and the device's fault log. Everything else in the state directory is
treated as continuity.

Also to confirm before relying on the downlink: `PredictiveStager` resolves its
queue path from the package directory, not from the state directory the app
passes in; check where that lands on the phone.

## Moving the Surface to another device (state-preserving)

    # on the phone that is currently the Surface
    ... strata_link handoff-checkpoint --state-dir <state dir>     # prints a token
    # on the new device (already paired), within an hour
    ... strata_link handoff-claim --state-dir <state dir> --token <token>

The old Surface checkpoints everything it holds on the laptop. While a
checkpoint is waiting, a claim without its token is refused (`handoff_pending`),
so a stateless device cannot take the role out from under it. The new device
claims with the token (epoch + 1), pulls every file, verifies each against its
hash, installs with a backup, and only then tells the laptop the migration is
complete. The old Surface learns it is `standby` on its next sync. A checkpoint
that nobody claims expires after an hour. Restart the app on the new device
after the pull (`restart_required`).

    ... strata_link verify --state-dir <state dir>

compares this device's state files against the laptop's, file by file, and
reports what still matches, differs, or is missing. A live Surface changes files
all the time, so right after a seed a few differ legitimately.

## Diagnostics

    python -m aurora_internal.dual_strata.strata_link status

shows the owner, epoch, last-seen time per Surface, applied sequence numbers
and the downlink outbox. On the phone the Hub row carries the same for its side.

## Recovery behaviour (covered by tests/test_strata_link.py)

- **Laptop asleep / no signal:** turns accumulate in the phone's outbox (up to
  5,000; an overflow is counted and shown, never silent) and flush in order on
  reconnect.
- **Response lost mid-air:** the batch is resent and recognised as already applied.
- **Phone killed between copy and consume:** the packet is not duplicated.
- **Laptop link state rebuilt:** downlink numbering restarts cleanly.
- **Wrong or missing secret, forged response, stale timestamp:** refused.

## Measured (loopback, this development machine — not phone-to-laptop)

- Idle sync round trip: ~1.6 ms.
- 200 turns lived offline (230 KB outbox) delivered in 7 exchanges, 0.23 s.

Real latency over a mobile network is unmeasured; the Hub row reports it live.

## Measured (state transfer, loopback)

Her real state directory (3,130 transferable files, 251.9 MB) seeded to an
empty directory through the real HTTP server: **28.3 s**, 3,130/3,130 files
verified, `verify` 3,130 match / 0 differ / 0 missing in 1.7 s; seeding again
sent **0 bytes** (5.2 s, all files recognised). Phone-to-laptop speed is
unmeasured.

## Not built yet / not verified

- **No physical two-device run has been done.** Everything above is verified on
  one machine (in-memory exchange between separate state directories, and the
  real HTTP server on loopback).
- No Hub button for seed/handoff; the bridge call `strata_link_transfer` and the
  command line exist.
- The laptop daemon does not reload state after a seed; a restart is needed.
- Sensory *guidance* going down only works while the laptop's subsurface writes
  guidance events; the sensory *snapshot* up only moves what the phone writes.
  Camera/microphone streams themselves are not carried (a snapshot is a
  description, not video).
- Running `aurora_daemon` natively on Windows has **not been tested**. It was
  developed on Linux. If it fails to boot, the log above says where; WSL2 is
  the fallback that runs the existing Linux setup unchanged.


## Hub controls (FIX-A125 follow-up)

Long-press the "Subsurface link" row in the Hub for: seed Subsurface, checkpoint
for a new Surface device (shows the token), claim Surface here (asks for the
token), verify. Tap still pairs. This Dart/Kotlin code was written by mirroring the
existing pairing flow and has **not been compiled or run**; the Python side it
calls (`strata_link_transfer_cmd`) is tested.

Authors: Sunni (Sir) Morningstar & Cael Devo
