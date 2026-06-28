# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""The single input chokepoint: a numbered menu that re-prompts until valid."""


def menu(title: str, options: list[str]) -> int:
    """Print a numbered menu and return the chosen index (0-based).

    Loops on invalid input instead of crashing. Returns when the player picks a
    valid number. On end-of-input (e.g. piped stdin runs out) returns the last
    option, treated as the safe "exit" choice by callers.
    """
    print()
    print(title)
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        try:
            raw = input("> ").strip()
        except EOFError:
            return len(options) - 1
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice - 1
        print(f"Invalid choice. Choose 1-{len(options)}.")
