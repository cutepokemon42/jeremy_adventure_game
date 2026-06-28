# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""XP -> level math. Level is always derived from XP so saves are easy to repair."""
from models import Player


def level_for_xp(xp: int) -> int:
    """Every 10 XP is one level. Level 1 at 0-9 XP, level 2 at 10-19, etc."""
    return max(1, xp // 10 + 1)


def level_down(player: Player) -> None:
    """Drop the player one level (minimum 1) as a death penalty.

    XP is set to the start of the new lower level so the formula stays
    consistent. Base max_hp and pwr are recalculated from scratch; equipment
    bonuses are applied on top as always, so they are not affected."""
    if player.level <= 1:
        player.xp = 0
        player.max_hp = 20
        player.pwr = 3
        return
    player.level -= 1
    player.xp = (player.level - 1) * 10   # first XP value of the new level
    player.max_hp = 20 + (player.level - 1) * 5
    player.pwr = 3 + (player.level - 1)


def apply_level(player: Player) -> None:
    """Raise the player to the level their XP earns, bumping stats and healing.

    No-op if XP hasn't crossed a threshold. Each level gained adds +5 max HP and
    +1 PWR, and a level-up heals to full.
    """
    new_level = level_for_xp(player.xp)
    if new_level <= player.level:
        return
    gained = new_level - player.level
    player.level = new_level
    player.max_hp += gained * 5
    player.pwr += gained
    player.hp = player.max_hp
