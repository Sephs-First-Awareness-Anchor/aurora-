# Aurora's private internet relay (one small hosted service)

Aurora's desktop and Android apps have **the relay client built in**.
Neither installs a VPN nor needs a router port forward. The gateway is a
separate publicly reachable web service whose *only* function is to match
encrypted request/reply packets. It is not another Aurora instance and
cannot read crystal contents, memories, signing secrets or the owner console.

## What needs hosting

A machine/service with an HTTPS domain and an always-running Python 3.11+
process. The gateway uses the standard library and stores only bounded
pending ciphertext **in memory**. The desktop re-registers after restarts.

1. Set a random, private 24+ character registration key in the hosted
   environment as `AURORA_RELAY_REGISTRATION_KEY`. This gates room creation.
   Keep it on the gateway and in Aurora desktop's protected configuration,
   never in the Android pairing link.
2. On the web host, run
   `python -m aurora_internal.dual_strata.relay_gateway` under a process
   manager such as systemd (example service file in this directory).
   It binds to **127.0.0.1:8795 only**.
3. Use an HTTPS reverse proxy, for example Caddy with Caddyfile.example
   and a public domain you control. Open port 443, not backend port 8795.
   Allow POST bodies up to 7 MiB and 35+ s exchange requests.
4. Verify `https://relay.your-domain.com/v1/health` responds.
   In Aurora desktop choose **Pair phone**, enter the relay's HTTPS URL,
   then the registration key. Aurora creates a room and copies a pairing link.
5. Paste that link in the Android **Hub → Pair with home**. Switch to
   cellular and tap **Test home connection**. Check the status of both apps.

These are one-time **hosting-side** steps. The installed desktop and
phone apps manage pairing, reconnect, LAN priority and offline behavior.
No terminal commands are required on either installed device.

The home desktop makes outbound HTTPS calls only. It never exposes the
owner Hub. The phone also makes outbound HTTPS calls from cellular.
Both encrypt entire already signed Strata packets using AES-GCM before
they reach the relay. The relay only sees opaque ciphertext, its mailbox
ID, random bearer token, timing and data sizes.

Keep the private pairing link out of messages and source control. This
reference gateway is for a privately operated Aurora relay, not a
public multitenant SaaS without added abuse prevention and quotas.

## Failure and fallback

- On trusted home Wi-Fi, the phone tries the direct signed LAN link first.
- If local fails, it tries the encrypted internet relay automatically.
- Home Ethernet works fine even if the home has no Wi-Fi.
- If home is asleep/offline, the Surface stays locally functional and
  queues eligible history; no gateway can provide a live sleeping home.
- Pending mailbox exchanges are not history archives. The devices'
  existing durable outboxes own recovery and re-delivery.
- If the relay restarts, the desktop re-registers its private room.

Initial real-device testing over cellular is required before declaring
remote pairing dependable. Ensure public DNS, TLS and always-on hosting.
