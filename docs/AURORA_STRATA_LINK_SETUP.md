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
| laptop → phone | subsurface projection, predictive frames | **off until enabled** (below) |

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

## Turning on the downlink

A projection only means something when it comes from a Subsurface that has
lived the same history as the Surface it colours. The laptop starts from its
own copy of her state, not the phone's. **Do not enable the downlink until the
laptop has been seeded with the phone's state.** That seeding step is not built
yet. When it is, enabling is one empty file on the laptop:

    aurora_state\strata_link\downlink_enabled

Also to confirm before enabling: `PredictiveStager` resolves its queue path
from the package directory, not from the state directory the app passes in;
check where that lands on the phone.

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

## Not built yet

- Seeding the laptop Subsurface from the phone's state (blocks the downlink).
- The full migration handshake (transfer of surface-owned state between devices).
- More channels: sensory snapshot up; sensory guidance, evidence bindings down.
- Running `aurora_daemon` natively on Windows has **not been tested**. It was
  developed on Linux. If it fails to boot, the log above says where; WSL2 is
  the fallback that runs the existing Linux setup unchanged.
