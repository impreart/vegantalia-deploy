#!/usr/bin/env python3
"""Demo für Progress Bar"""

import time

print("🎬 Progress Bar Demo")
print()

# Simuliere Übersetzung von 5 Rezepten
recipes = ["Käsespätzle", "Shakshuka", "Gulasch", "Pad Thai", "Ramen"]
total = len(recipes)

for idx, recipe in enumerate(recipes, 1):
    percentage = (idx / total) * 100
    bar_length = 30
    filled = int(bar_length * idx / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\r  [{bar}] {percentage:.0f}% | [{idx}/{total}] {recipe:<20} 🆕", end='', flush=True)
    time.sleep(0.5)

print()
print()
print("✅ Fertig!")
