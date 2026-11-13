# Windows Subsurface hub

Run one continuous Subsurface on the Windows laptop. The Galaxy A16 and laptop can each host the existing `surface` profile for the **same Surface**. The hub grants one device the active lease. Durable learning, pressure, Praxis, and continuity belong to Subsurface. The active Surface owns present sensory intake, live interpretation, expression, and its working state.

## Runtime connections

| Direction | Existing contract | Integration point |
| --- | --- | --- |
| Hub to active Surface | Softened Subsurface projection, presence frame, predictive perspectives | Push updates ahead of use and keep the newest applicable batch in memory on the active device. |
| Active Surface to hub | Sensory snapshot, turn-open, interpreted turn, evidence need | Carry the existing packets with the lease epoch and canonical turn ID. |
| Active Surface to hub | Surface continuity packet | Acknowledge durable receipt before releasing the turn. Retry with the same ID. |
| Current Surface to target through the hub | Surface checkpoint | Freeze and transfer the complete Surface-owned state with its original Surface ID and one checkpoint revision. |
| Hub to registered devices | Device lease and sleep request | Suspend capture and new input on the old host. Issue an active lease after the target has restored the checkpoint. |

Keep the laptop's Subsurface running through every transfer. A paired phone uses `boot_aurora(runtime_profile="surface")` with its local sensory and expression paths. The all-in-one Android initializer starts Subsurface workers, so paired startup needs an explicit branch.

Both existing profiles instantiate working memory and start a metabolic clock. In paired mode, keep Subsurface's internal working memory distinct from Surface's moving state and assign each periodic step to its owning stratum. Use the accepted continuity and current presence inputs as compact context for Subsurface's predictor.

## State ownership and transfer

Surface has one writable state at a time. Transfer the complete Surface-owned state, including working memory, session and referent anchors, pending clarification and expression, the current frame, and the session state in `genealogy_surface`. Supply canonical genealogy from Subsurface as a read-only input. Inventory the live fields against the real Surface entry points before defining the versioned serializer. Preserve the types and bounds of runtime collections. Reacquire the new device's sensors, handles, permissions, and clock on arrival. The hub stores one opaque checkpoint as custodian and retains its own separate Subsurface continuity.

1. The operator selects an online registered target. The hub closes new admission on the active Surface while its current turn and continuity handoff finish.
2. The old Surface suspends local capture and expression. The hub commits the frozen checkpoint and retires the old lease in the same write.
3. The target restores the checkpoint and acknowledges its revision and digest. The hub issues a new epoch to that device. After acknowledgement, clear the temporary copies on the device that released the lease. The target becomes the only writer of the resumed Surface.
4. If the source disconnects before freezing, wait out its lease and require the operator to choose recovery from the last committed checkpoint. A hub restart respects the full previous lease lifetime. A restart after freezing resumes the pending restore with the saved checkpoint.

Use authenticated, encrypted connections between paired devices. Devices derive local expiry from the hub's lease duration and their own monotonic clock, accounting for request time. One authority instance owns the hub state directory. Device suspension is independent of Aurora's organism sleep cycle.

## Anticipatory framing

Keep the Subsurface predictor running independently of Surface requests. Stage several plausible perspectives from the current pressures, unresolved meaning and the latest accepted continuity. Send them as one batch. Send a fresh baseline to the target during restoration, then refresh the batch when an admitted turn opens, interpretation changes, or new evidence changes the expected needs.

Reuse the existing PredictiveStager and DCE inputs. The publisher hands off completed frames to a transport thread. Tag a batch with the Surface ID, lease epoch, context revision, sequence, and remaining useful lifetime. Surface reads the matching in-memory batch without a network round trip. Invalidate it when its scope or evidence changes. Treat staged material as hypotheses and apply actual input through the normal DCE and grounding gates. If fresh Subsurface evidence is essential, use the existing phase boundary with a bounded wait for that evidence.

Track the rate of turns with usable frames already in cache, stale and invalidated frames, and time spent waiting for required phases. Compare the paired path with a local Surface/Subsurface run on the same turns.

## Draft scope

`SurfaceDevicePresence` supplies registration, lease fencing, turn drain, and checkpoint transfer. Tests cover exact state restoration, identity preservation, disconnects, restart, and concurrent admission. The existing PredictiveStager now supports a batched publisher and a Surface-side inbox. Tests exercise the actual staging and harvest path with in-memory delivery.

The next integration is the authenticated link, full Surface-state serialization, and routing the real packets in the Windows and Android entry points. Verify that a real referent and pending clarification survive a device handoff while Subsurface continues to publish input. Bring the phone's existing durable continuity over through a deliberate export and import during setup.
