// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Constrained Multiprocessing — Aurora IS the scheduler.
//
// Other processes are "organs": autonomous units with their own axis profiles.
// On each frame, Aurora computes the dot-product alignment between her current
// axis state and each organ's axis profile.  The highest-aligned organ gets
// the next quantum.  Aurora cannot be preempted — the face render always runs
// first; organs run in the leftover slice.
//
// There is no "fairness" imposed from outside — alignment IS fairness.
// An organ that needs to run should have a profile that aligns with Aurora's
// state when it needs to run.  That is the constraint physics of scheduling.
pub mod organ;
pub mod scheduler;
