# Authors: Sunni (Sir) Morningstar & Cael Devo

import sys
import os

# Add aurora_core_ai to path
sys.path.append(os.path.join(os.getcwd(), 'aurora_core_ai'))

try:
    from aurora_expression_perception import SentenceComposer, LexicalMemory, VoiceGenome, ExpressionOffspring, AssemblyResult
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

lexicon = LexicalMemory()
voice = VoiceGenome()
composer = SentenceComposer(lexicon, voice)

# Test conjugation for "I"
print("Testing 'I' conjugation...")
print(f"I + is -> {composer._conjugate_verb('is', 'I', '{V}')}")
print(f"I + are -> {composer._conjugate_verb('are', 'I', '{V}')}")
print(f"I + does -> {composer._conjugate_verb('does', 'I', '{V}')}")

# Test conjugation for "you"
print("\nTesting 'you' conjugation...")
print(f"you + is -> {composer._conjugate_verb('is', 'you', '{V}')}")
print(f"you + am -> {composer._conjugate_verb('am', 'you', '{V}')}")
print(f"you + has -> {composer._conjugate_verb('has', 'you', '{V}')}")
print(f"you + does -> {composer._conjugate_verb('does', 'you', '{V}')}")

# Test absorption skip for corrections
print("\nTesting absorption skip...")
old_count = len(composer.pool['neutral'])
composer.absorb("Stop saying what is you doing.")
new_count = len(composer.pool['neutral'])
if new_count == old_count:
    print("✓ Successfully skipped correction absorption.")
else:
    print(f"✗ Failed to skip: {new_count} > {old_count}")

composer.absorb("The weather is beautiful today.")
final_count = len(composer.pool['neutral'])
if final_count > new_count:
    print("✓ Successfully absorbed natural pattern.")
else:
    print("✗ Failed to absorb natural pattern.")
