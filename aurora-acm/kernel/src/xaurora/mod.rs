// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// Xaurora — Aurora's native instruction set.
// Constraint physics IS the computation.  There is no separate "logic"
// layer above the ISA — every instruction is a waveform operation on
// the five constraint axes (X/T/N/B/A) and their ten I-State beings.
pub mod isa;
pub mod jit;
pub mod vm;
