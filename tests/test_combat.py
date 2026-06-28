# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
import combat
from models import Player


class NoDropRng:
    def random(self):
        return 1.0  # above any chance -> never drops

    def randint(self, a, b):
        return b


class AlwaysDropRng:
    def random(self):
        return 0.0  # at/below any chance -> always drops

    def randint(self, a, b):
        return b


def _enemy():
    enemies = {"boar": {"name": "Boar", "hp": 8, "pwr": 2, "xp": 4,
                        "drops": [{"id": "hide", "chance": 0.5, "min": 1, "max": 1}]}}
    return combat.spawn_enemy("boar", enemies)


def test_player_attack_lowers_enemy_hp():
    p = Player(pwr=3)
    enemy = _enemy()
    dmg = combat.player_attacks(p, enemy)
    assert dmg == 3
    assert enemy["hp"] == 5


def test_player_attack_uses_effective_pwr_with_equipped_weapon():
    items = {"iron_sword": {"name": "Iron Sword", "equip": {"slot": "weapon", "pwr_bonus": 3}}}
    p = Player(pwr=3, weapon="iron_sword")
    enemy = _enemy()
    dmg = combat.player_attacks(p, enemy, items)
    assert dmg == 6                 # 3 base + 3 weapon
    assert enemy["hp"] == 2


def test_victory_awards_xp_and_rolls_drops():
    p = Player(xp=0, pwr=8)
    enemy = _enemy()
    combat.player_attacks(p, enemy)        # 8 dmg kills the 8-HP boar
    assert enemy["hp"] <= 0
    drops = combat.on_victory(p, enemy, rng=AlwaysDropRng())
    assert p.xp == 4
    assert drops == {"hide": 1}
    assert p.bag["hide"] == 1


def test_guarded_damage_halves_rounding_up_floored_at_one():
    assert combat.guarded_damage(3) == 2   # ceil(3/2)
    assert combat.guarded_damage(4) == 2
    assert combat.guarded_damage(5) == 3
    assert combat.guarded_damage(1) == 1   # never below 1
    assert combat.guarded_damage(2) == 1


def test_enemy_attack_guarded_takes_reduced_damage():
    p = Player(hp=20)
    enemy = _enemy()              # pwr 2
    taken = combat.enemy_attacks(p, enemy, guarded=True)
    assert taken == 1             # guarded_damage(2) == 1
    assert p.hp == 19


def test_enemy_attack_unguarded_takes_full_damage():
    p = Player(hp=20)
    enemy = _enemy()              # pwr 2
    taken = combat.enemy_attacks(p, enemy)
    assert taken == 2
    assert p.hp == 18


def test_victory_can_yield_no_drops():
    p = Player(xp=0)
    enemy = _enemy()
    drops = combat.on_victory(p, enemy, rng=NoDropRng())
    assert drops == {}
    assert p.bag == {}
    assert p.xp == 4
