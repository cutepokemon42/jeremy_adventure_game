# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
import pytest

import storage
from models import Player


# --- item validation -------------------------------------------------------

def test_bad_consumable_effect_raises():
    items = {"potion": {"name": "Potion", "type": "consumable", "effect": {"kind": "explode"}}}
    with pytest.raises(ValueError):
        storage.validate_data({}, items, {}, {})


def test_consumable_nonpositive_heal_raises():
    items = {"potion": {"name": "Potion", "type": "consumable", "effect": {"kind": "heal", "amount": 0}}}
    with pytest.raises(ValueError):
        storage.validate_data({}, items, {}, {})


def test_bad_equip_slot_raises():
    items = {"hat": {"name": "Hat", "type": "craftable", "equip": {"slot": "head", "pwr_bonus": 1}}}
    with pytest.raises(ValueError):
        storage.validate_data({}, items, {}, {})


def test_equip_missing_bonus_key_raises():
    items = {"sword": {"name": "Sword", "type": "craftable", "equip": {"slot": "weapon"}}}
    with pytest.raises(ValueError):
        storage.validate_data({}, items, {}, {})


# --- save round-trip for equipment slots -----------------------------------

def test_player_equipment_round_trips(tmp_path):
    path = tmp_path / "save.json"
    world = {"spawn": {"name": "Spawn", "description": "", "enemies": [], "gather": []}}
    items = {"iron_sword": {"name": "Iron Sword", "type": "craftable",
                            "equip": {"slot": "weapon", "pwr_bonus": 3}},
             "leather_armor": {"name": "Leather Armor", "type": "craftable",
                               "equip": {"slot": "armor", "max_hp_bonus": 10}}}
    player = Player(location="spawn", weapon="iron_sword", armor="leather_armor", bag={})
    storage.save_game(path, player)
    loaded = storage.load_game(path, world, items)
    assert loaded.weapon == "iron_sword"
    assert loaded.armor == "leather_armor"


def test_save_unknown_equipped_item_raises(tmp_path):
    path = tmp_path / "save.json"
    world = {"spawn": {"name": "Spawn", "description": "", "enemies": [], "gather": []}}
    storage.save_game(path, Player(location="spawn", weapon="phantom_blade"))
    with pytest.raises(ValueError):
        storage.load_game(path, world, {})
