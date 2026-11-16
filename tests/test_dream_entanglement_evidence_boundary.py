"""Regression contract for speculative dream entanglement.

This test is deliberately expected to FAIL against the existing implementation.
It must pass before a runtime change to the dream/genealogy boundary is merged.
No real user state is loaded or modified.
"""
import unittest
from unittest.mock import patch

from aurora_quantum_dream_substrate import CrystalEntanglementRegistry


class FakeGenealogy:
    def __init__(self):
        self.recent_promotions = ["shared_alpha", "shared_beta"]
        self.promotions = []

    def tick_crystal_promotion(self, concept, *, delta, source):
        self.promotions.append((concept, delta, source))


class DreamEntanglementEvidenceBoundaryTest(unittest.TestCase):
    def test_dream_only_association_cannot_promote_earned_genealogy(self):
        genealogy = FakeGenealogy()
        registry = CrystalEntanglementRegistry()
        with patch("aurora_quantum_dream_substrate.random.uniform", return_value=0.8), patch(
            "aurora_quantum_dream_substrate.random.random", return_value=0.0
        ):
            self.assertEqual(registry.auto_entangle_from_genealogy({"genealogy": genealogy}), 1)
            registry.propagate({"genealogy": genealogy})
        self.assertEqual(
            genealogy.promotions, [],
            "Dream-only inferred association must not create earned genealogy promotions",
        )

    def test_unrelated_short_names_do_not_create_fake_siblings(self):
        genealogy = FakeGenealogy()
        genealogy.recent_promotions = ["apple", "apply"]
        registry = CrystalEntanglementRegistry()
        registry.auto_entangle_from_genealogy({"genealogy": genealogy})
        self.assertEqual(
            registry._pairs, [],
            "A common five-character prefix is not canonical shared ancestry",
        )


if __name__ == "__main__":
    unittest.main()
