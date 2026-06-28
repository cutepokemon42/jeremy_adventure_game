# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from models import (
    Player,
    effective_max_hp,
    effective_pwr,
    equip_item,
    use_item,
)

ITEMS = {
    "healing_poultice": {"name": "Healing Poultice", "type": "consumable",
                         "effect": {"kind": "heal", "amount": 12}},
    "wooden_spear": {"name": "Wooden Spear", "type": "craftable",
                     "equip": {"slot": "weapon", "pwr_bonus": 1}},
    "iron_sword": {"name": "Iron Sword", "type": "craftable",
                   "equip": {"slot": "weapon", "pwr_bonus": 3}},
    "leather_armor": {"name": "Leather Armor", "type": "craftable",
                      "equip": {"slot": "armor", "max_hp_bonus": 10}},
    "wood": {"name": "Wood", "type": "material"},
}


# --- use_item --------------------------------------------------------------

def test_use_heals_and_consumes_one():
    p = Player(hp=5, max_hp=20, bag={"healing_poultice": 2})
    result = use_item(p, "healing_poultice", ITEMS)
    assert result["ok"] is True
    assert result["healed"] == 12
    assert p.hp == 17
    assert p.bag["healing_poultice"] == 1  # exactly one consumed


def test_use_caps_at_effective_max_hp():
    p = Player(hp=15, max_hp=20, bag={"healing_poultice": 1})
    result = use_item(p, "healing_poultice", ITEMS)
    assert p.hp == 20                 # capped, not 27
    assert result["healed"] == 5
    assert "healing_poultice" not in p.bag


def test_use_cap_includes_armor_bonus():
    p = Player(hp=20, max_hp=20, armor="leather_armor", bag={"healing_poultice": 1})
    use_item(p, "healing_poultice", ITEMS)
    assert p.hp == 30                 # cap is 20 base + 10 armor


def test_use_missing_item_fails_and_changes_nothing():
    p = Player(hp=5, bag={})
    result = use_item(p, "healing_poultice", ITEMS)
    assert result["ok"] is False
    assert result["reason"] == "missing"
    assert p.hp == 5


def test_use_non_consumable_fails():
    p = Player(hp=5, bag={"wood": 1})
    result = use_item(p, "wood", ITEMS)
    assert result["ok"] is False
    assert result["reason"] == "not_consumable"
    assert p.bag == {"wood": 1}


# --- equip_item ------------------------------------------------------------

def test_equip_weapon_sets_slot_and_consumes_from_bag():
    p = Player(pwr=3, bag={"wooden_spear": 1})
    result = equip_item(p, "wooden_spear", ITEMS)
    assert result["ok"] is True
    assert p.weapon == "wooden_spear"
    assert "wooden_spear" not in p.bag           # moved out of the bag onto the slot
    assert effective_pwr(p, ITEMS) == 4          # 3 base + 1 weapon
    assert p.pwr == 3                            # base PWR never mutated


def test_equip_swap_returns_previous_to_bag():
    p = Player(pwr=3, weapon="wooden_spear", bag={"iron_sword": 1})
    result = equip_item(p, "iron_sword", ITEMS)
    assert result["ok"] is True
    assert result["previous"] == "wooden_spear"
    assert p.weapon == "iron_sword"
    assert p.bag["wooden_spear"] == 1            # old weapon stowed, not lost
    assert effective_pwr(p, ITEMS) == 6          # 3 base + 3 sword


def test_equip_armor_raises_effective_max_hp_only():
    p = Player(hp=20, max_hp=20, bag={"leather_armor": 1})
    equip_item(p, "leather_armor", ITEMS)
    assert p.armor == "leather_armor"
    assert effective_max_hp(p, ITEMS) == 30
    assert p.max_hp == 20                         # base untouched
    assert p.hp == 20                             # equipping is headroom, not a heal


def test_equip_non_equippable_fails():
    p = Player(bag={"wood": 1})
    result = equip_item(p, "wood", ITEMS)
    assert result["ok"] is False
    assert result["reason"] == "not_equippable"
    assert p.weapon is None
    assert p.bag == {"wood": 1}


def test_effective_stats_without_equipment_are_base():
    p = Player(pwr=3, max_hp=20)
    assert effective_pwr(p, ITEMS) == 3
    assert effective_max_hp(p, ITEMS) == 20
