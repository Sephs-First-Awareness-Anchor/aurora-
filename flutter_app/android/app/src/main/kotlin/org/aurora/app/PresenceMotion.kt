package org.aurora.app

// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// PresenceMotion.kt -- how her line of presence moves (surface restructure
// 4b).  Plain Kotlin with no Android classes, so it can be unit-tested.
//
// Every property of the line is a continuous function of her own state or
// her own voice.  There are no states, moods or set animations:
//   * at rest, colour, thickness, slow drift and tension come from her five
//     axes (with their polarity around 0.5) and her live pressure field;
//   * while she listens, her hearing (the microphone level she already
//     receives) moves it;
//   * while she speaks, the line traces her actual voice waveform; each word
//     adds a soft nudge, which is also the whole voice signal on a device
//     that refuses the waveform reader.
// Her state only moves targets.  Damped springs with a dead-band and speed
// and acceleration caps draw toward them, and each point of the line is
// limited in how far it can move per frame, so nothing snaps.

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

private fun clampD(v: Double, lo: Double, hi: Double): Double = if (v < lo) lo else if (v > hi) hi else v

/** A damped spring toward a target, with a dead-band and rate/acceleration caps. */
class SpringK(
    initial: Double,
    val stiffness: Double = 60.0,
    val damping: Double = 14.0,
    val deadBand: Double = 0.02,
    val maxRate: Double = 2.5,
    val maxAccel: Double = 30.0,
    val lo: Double = -10.0,
    val hi: Double = 10.0,
) {
    var value: Double = initial
        private set
    var velocity: Double = 0.0
        private set
    var target: Double = initial
        private set
    private var accepted: Double = initial

    /** Move the target only past the dead-band.  True when it moved. */
    fun setTarget(next: Double): Boolean {
        val t = clampD(if (next.isFinite()) next else accepted, lo, hi)
        if (abs(t - accepted) < deadBand) return false
        accepted = t
        target = t
        return true
    }

    fun step(dt: Double) {
        if (!(dt > 0.0)) return
        var remaining = min(dt, 0.5)
        while (remaining > 1e-9) {
            val h = min(remaining, 1.0 / 240.0)
            val a = clampD(stiffness * (target - value) - damping * velocity, -maxAccel, maxAccel)
            velocity = clampD(velocity + a * h, -maxRate, maxRate)
            value += velocity * h
            if (value < lo) { value = lo; if (velocity < 0) velocity = 0.0 }
            else if (value > hi) { value = hi; if (velocity > 0) velocity = 0.0 }
            remaining -= h
        }
    }

    val settled: Boolean
        get() = abs(target - value) <= max(deadBand * 0.5, 1e-4) && abs(velocity) <= maxRate * 0.02
}

class PresenceMotion(val points: Int = 96) {
    // Colour, in degrees (unwrapped) and 0..1.
    val hue = SpringK(270.0, 18.0, 8.5, 2.0, 90.0, 600.0, 120.0, 420.0)
    val saturation = SpringK(0.5, 18.0, 8.5, 0.01, 0.6, 4.0, 0.0, 1.0)
    val brightness = SpringK(0.6, 18.0, 8.5, 0.01, 0.6, 4.0, 0.0, 1.0)
    /** Line thickness in dp. */
    val thickness = SpringK(2.0, 40.0, 10.0, 0.05, 6.0, 60.0, 1.0, 5.0)
    /** How far the resting line drifts, 0..1 of the available height. */
    val tension = SpringK(0.25, 30.0, 9.0, 0.01, 1.5, 12.0, 0.0, 1.0)
    /** How fast the resting drift travels, cycles per second. */
    val driftRate = SpringK(0.2, 20.0, 8.0, 0.01, 0.6, 3.0, 0.02, 0.8)
    /** Her hearing and her voice: no dead-band, quick springs. */
    val hearing = SpringK(0.0, 90.0, 18.0, 0.0, 6.0, 80.0, 0.0, 1.0)
    val voice = SpringK(0.0, 160.0, 22.0, 0.0, 9.0, 160.0, 0.0, 1.0)

    /** Each point of the line may move at most this far per second (in units of the line's amplitude). */
    val maxPointRate = 9.0

    private var phase = 0.0
    private val drawn = FloatArray(points)
    private val want = FloatArray(points)

    /** axes: X, T, N, B, A (0..1).  pressure: per axis, may be empty. */
    fun setState(axes: DoubleArray, pressure: DoubleArray) {
        fun s(i: Int) = 2.0 * (clampD(axes.getOrElse(i) { 0.5 }, 0.0, 1.0) - 0.5)
        val x = s(0); val t = s(1); val n = s(2); val b = s(3); val a = s(4)
        var strain = 0.0
        var count = 0
        for (p in pressure) if (p.isFinite()) { strain += abs(p); count++ }
        strain = if (count == 0) 0.0 else clampD(strain / count, 0.0, 1.0)
        val pa = clampD(pressure.getOrElse(4) { 0.0 }, -1.0, 1.0)

        hue.setTarget(270.0 + 55.0 * a - 35.0 * b + 25.0 * t + 15.0 * pa)
        saturation.setTarget(clampD(0.50 + 0.22 * abs(a) + 0.12 * x + 0.16 * strain, 0.2, 1.0))
        brightness.setTarget(clampD(0.62 + 0.20 * n + 0.10 * x, 0.25, 1.0))
        thickness.setTarget(clampD(2.0 + 0.8 * x + 0.6 * n + 1.2 * strain, 1.0, 5.0))
        tension.setTarget(clampD(0.18 + 0.30 * strain + 0.10 * abs(t) + 0.08 * max(0.0, a), 0.0, 1.0))
        driftRate.setTarget(clampD(0.18 + 0.12 * n + 0.10 * x + 0.15 * strain, 0.02, 0.8))
    }

    fun setHearing(level: Double) { hearing.setTarget(clampD(level, 0.0, 1.0)) }

    fun setVoice(level: Double) { voice.setTarget(clampD(level, 0.0, 1.0)) }

    fun step(dt: Double) {
        if (!(dt > 0.0)) return
        val d = min(dt, 0.5)
        for (c in arrayOf(hue, saturation, brightness, thickness, tension, driftRate, hearing, voice)) c.step(d)
        phase = (phase + 2.0 * PI * driftRate.value * d) % (2000.0 * PI)
    }

    /**
     * The line's shape this frame, as offsets in -1..1 of its available
     * height, one per point.  [wave] is her voice waveform in -1..1 (any
     * length), or null when no waveform is available.
     */
    fun shape(dt: Double, wave: FloatArray?): FloatArray {
        val v = voice.value
        val hr = hearing.value
        val ten = tension.value
        for (i in 0 until points) {
            val u = i.toDouble() / (points - 1)
            // Taper toward both ends so the line stays anchored at the edges.
            val taper = sin(PI * u)
            var y = ten * 0.5 * (0.6 * sin(2 * PI * 1.5 * u + phase) + 0.4 * sin(2 * PI * 3.7 * u - phase * 1.3))
            y += hr * 0.45 * sin(2 * PI * 9.0 * u + phase * 4.0)
            y += if (wave != null && wave.isNotEmpty()) {
                val idx = min(wave.size - 1, (u * (wave.size - 1)).toInt())
                v * wave[idx].toDouble() * 1.4
            } else {
                v * 0.7 * sin(2 * PI * 6.0 * u + phase * 6.0)
            }
            want[i] = clampD(y * taper, -1.0, 1.0).toFloat()
        }
        // Each point glides toward where it wants to be, with a cap on how far
        // it can move this frame.
        val d = if (dt > 0.0) min(dt, 0.5) else 0.0
        val alpha = 1.0 - exp(-d * 30.0)
        val cap = maxPointRate * d
        for (i in 0 until points) {
            val step = clampD((want[i] - drawn[i]) * alpha, -cap, cap)
            drawn[i] = (drawn[i] + step).toFloat()
        }
        return drawn.copyOf()
    }

    companion object {
        /** Root-mean-square level of an 8-bit Visualizer waveform, 0..1. */
        fun levelOf(wave: FloatArray?): Double {
            if (wave == null || wave.isEmpty()) return 0.0
            var sum = 0.0
            for (s in wave) sum += s.toDouble() * s
            return clampD(sqrt(sum / wave.size) * 2.5, 0.0, 1.0)
        }

        /** Visualizer gives unsigned 8-bit samples centred on 128. */
        fun fromUnsigned8(bytes: ByteArray): FloatArray =
            FloatArray(bytes.size) { i -> ((bytes[i].toInt() and 0xFF) - 128) / 128f }
    }
}
