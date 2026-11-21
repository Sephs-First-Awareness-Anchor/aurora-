package org.aurora.app

// Authors: Sunni (Sir) Morningstar & Cael Devo
//
// PresenceMotionTest -- her line of presence is smooth, never twitchy, and
// still reaches the full value of a real change (surface restructure 4b).

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin
import kotlin.random.Random

class PresenceMotionTest {

    private fun springs(m: PresenceMotion) = listOf(
        m.hue, m.saturation, m.brightness, m.thickness, m.tension, m.driftRate, m.hearing, m.voice,
    )

    /** A recorded-style voice waveform: a few formant-like tones, 8-bit unsigned. */
    private fun voiceBytes(frame: Int): ByteArray = ByteArray(256) { i ->
        val t = (frame * 256 + i) / 8000.0
        val s = 0.45 * sin(2 * PI * 180 * t) + 0.25 * sin(2 * PI * 720 * t) + 0.1 * sin(2 * PI * 2400 * t)
        (128 + (s * 120).toInt()).coerceIn(0, 255).toByte()
    }

    @Test
    fun noisyStateAndVoiceKeepEveryValueContinuous() {
        val rng = Random(11)
        val m = PresenceMotion()
        val dt = 1.0 / 60.0
        var prevShape = m.shape(dt, null)
        var prevValues = springs(m).map { it.value }
        for (frame in 0 until 60 * 30) {
            if (frame % 60 == 0) {
                val jump = rng.nextDouble() < 0.15
                val axes = DoubleArray(5) { if (jump) rng.nextDouble() else 0.5 + (rng.nextDouble() - 0.5) * 0.04 }
                val pressure = DoubleArray(5) { if (jump) rng.nextDouble() else 0.0 }
                m.setState(axes, pressure)
            }
            val speaking = (frame / 90) % 2 == 1
            val wave = if (speaking) PresenceMotion.fromUnsigned8(voiceBytes(frame)) else null
            m.setVoice(PresenceMotion.levelOf(wave))
            m.setHearing(if (!speaking) rng.nextDouble() * 0.5 else 0.0)
            m.step(dt)
            val shape = m.shape(dt, wave)
            for (i in shape.indices) {
                val change = abs(shape[i] - prevShape[i])
                assertTrue("point $i jumped by $change", change <= m.maxPointRate * dt + 1e-6)
                assertTrue("point $i is not finite", shape[i].isFinite())
                assertTrue("point $i left the line's height", abs(shape[i]) <= 1.0f)
            }
            val values = springs(m).map { it.value }
            for ((k, s) in springs(m).withIndex()) {
                val change = abs(values[k] - prevValues[k])
                assertTrue("spring $k jumped by $change", change <= s.maxRate * dt + 1e-9)
            }
            prevShape = shape
            prevValues = values
        }
    }

    @Test
    fun aLargeRealShiftStillReachesItsFullValue() {
        val m = PresenceMotion()
        m.setState(doubleArrayOf(0.95, 0.2, 0.9, 0.1, 0.95), doubleArrayOf(0.6, 0.6, 0.6, 0.6, 0.6))
        for (i in 0 until 60 * 6) m.step(1.0 / 60.0)
        for (s in listOf(m.hue, m.saturation, m.brightness, m.thickness, m.tension, m.driftRate)) {
            assertEquals(s.target, s.value, maxOf(s.deadBand, 1e-3))
            assertTrue(s.settled)
        }
    }

    @Test
    fun jitterSmallerThanTheDeadBandNeverMovesIt() {
        val m = PresenceMotion()
        m.setState(doubleArrayOf(0.5, 0.5, 0.5, 0.5, 0.5), DoubleArray(0))
        for (i in 0 until 60 * 4) m.step(1.0 / 60.0)
        val before = listOf(m.hue, m.saturation, m.brightness, m.thickness).map { it.value }
        for (i in 0 until 200) {
            m.setState(doubleArrayOf(0.5 + if (i % 2 == 0) 0.002 else -0.002, 0.5, 0.5, 0.5, 0.5), DoubleArray(0))
            m.step(1.0 / 60.0)
        }
        val after = listOf(m.hue, m.saturation, m.brightness, m.thickness).map { it.value }
        for (k in before.indices) assertEquals(before[k], after[k], 1e-6)
    }

    @Test
    fun withoutAWaveformHerWordsStillMoveTheLine() {
        val m = PresenceMotion()
        m.setVoice(0.6)
        var moved = 0.0
        for (i in 0 until 30) {
            m.step(1.0 / 60.0)
            moved = maxOf(moved, m.shape(1.0 / 60.0, null).maxOf { abs(it).toDouble() })
        }
        assertTrue("the line stayed flat while she spoke", moved > 0.05)
    }
}
