from foundational_contract import FoundationalContract
from aurora_ivm import IVMLattice, RecursionLevel
from aurora_internal.aurora_evolution_chamber import EvolutionaryChamber

# --- Setup ---
contract = FoundationalContract()
lattice  = IVMLattice(contract, max_nodes=1000)
chamber  = EvolutionaryChamber(lattice)

print("Starting live evolution run...\n")

# --- Live loop ---
for step in range(2000):
    lattice.tick(dt=0.1, level=RecursionLevel.SURFACE)
    event = chamber.tick()

    if event:
        print(
            f"[Tick {event.tick}] "
            f"Relief: "
            f"E={event.energy_relief} "
            f"F={event.flux_relief} "
            f"G={event.gradient_relief} "
            f"Multi={event.multi_channel}"
        )

# --- Summary ---
print("\n--- Chamber Summary ---")
print(chamber.miner.summary())
