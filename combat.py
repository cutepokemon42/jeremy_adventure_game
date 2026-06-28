# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Combat resolution. Pure functions over Player + a live enemy dict, no I/O,
so fights are deterministic and unit-testable (pass a fake rng)."""
import random

from leveling import apply_level
from models import Player, add_item, effective_max_hp, effective_pwr


def spawn_enemy(enemy_id: str, enemies: dict, world_scale: float = 1.0) -> dict:
    """Build a live, mutable enemy instance from its definition."""
    d = enemies[enemy_id]
    hp = max(d["hp"], round(d["hp"] * world_scale))
    pwr = max(d["pwr"], round(d["pwr"] * world_scale))
    return {
        "id": enemy_id,
        "name": d["name"],
        "hp": hp,
        "max_hp": hp,
        "pwr": pwr,
        "xp": d["xp"],
        "drops": d.get("drops", []),
    }


def spawn_dungeon_enemy(enemy_id: str, enemies: dict, player: Player, items: dict, difficulty: dict) -> dict:
    """Like spawn_enemy but scales HP and PWR relative to the player's current stats.

    hp_ratio  — enemy HP as a fraction of the player's effective max HP
    pwr_ratio — enemy PWR as a fraction of the player's effective PWR

    The result is floored at the enemy's base stat so dungeon enemies are always
    at least as tough as their normal version, and scale up as the player grows."""
    d = enemies[enemy_id]
    hp_ratio = difficulty.get("hp_ratio", 1.0)
    pwr_ratio = difficulty.get("pwr_ratio", 1.0)
    scaled_hp = max(d["hp"], int(effective_max_hp(player, items) * hp_ratio))
    scaled_pwr = max(d["pwr"], int(effective_pwr(player, items) * pwr_ratio))
    return {
        "id": enemy_id,
        "name": d["name"],
        "hp": scaled_hp,
        "max_hp": scaled_hp,
        "pwr": scaled_pwr,
        "xp": d["xp"],
        "drops": d.get("drops", []),
    }


def player_attacks(player: Player, enemy: dict, items: dict | None = None,
                   dmg_mult: float = 1.0) -> int:
    """Deal the player's effective PWR to the enemy, scaled by dmg_mult.

    When items is given the equipped weapon's bonus is included; without it the
    bare base PWR is used (keeps the simple combat-math tests deterministic).
    dmg_mult < 1.0 is used for ranged weapons (kiting penalty)."""
    dmg = effective_pwr(player, items) if items is not None else player.pwr
    dmg = max(1, round(dmg * dmg_mult))
    enemy["hp"] -= dmg
    return dmg


def enemy_attacks(player: Player, enemy: dict, guarded: bool = False) -> int:
    """Apply the enemy's hit to the player. When guarded, the hit is reduced via
    guarded_damage. Returns the damage actually taken."""
    dmg = guarded_damage(enemy["pwr"]) if guarded else enemy["pwr"]
    player.hp -= dmg
    return dmg


def guarded_damage(enemy_pwr: int) -> int:
    """Damage the player takes while defending: half the enemy's PWR, rounded up,
    floored at 1 (a guard never fully negates a blow). Pure and deterministic."""
    return max(1, (enemy_pwr + 1) // 2)


def roll_drops(enemy: dict, rng=random) -> dict[str, int]:
    """Roll each drop independently against its chance. Returns item -> qty."""
    drops: dict[str, int] = {}
    for d in enemy["drops"]:
        if rng.random() <= d["chance"]:
            n = rng.randint(d["min"], d["max"])
            if n > 0:
                drops[d["id"]] = drops.get(d["id"], 0) + n
    return drops


def on_victory(player: Player, enemy: dict, rng=random) -> dict[str, int]:
    """Award XP (and level up if earned) and add rolled drops to the bag."""
    player.xp += enemy["xp"]
    apply_level(player)
    drops = roll_drops(enemy, rng)
    for item_id, n in drops.items():
        add_item(player, item_id, n)
    return drops
