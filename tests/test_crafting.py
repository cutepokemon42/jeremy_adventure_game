# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from actions import craft
from models import GameState, Player


def _state(bag):
    recipes = {
        "wooden_spear": {
            "name": "Wooden Spear",
            "requires": {"wood": 3},
            "creates": {"wooden_spear": 1},
        }
    }
    items = {
        "wood": {"name": "Wood", "type": "material"},
        "wooden_spear": {"name": "Wooden Spear", "type": "craftable",
                         "equip": {"slot": "weapon", "pwr_bonus": 1}},
    }
    return GameState(player=Player(pwr=3, bag=dict(bag)), world={}, items=items, recipes=recipes)


def test_craft_consumes_inputs_and_produces_output_without_bumping_stats():
    # Crafting only creates the item; the PWR bump comes later from equipping it,
    # so crafting twice never permanently stacks PWR.
    state = _state({"wood": 3})
    assert craft(state, "wooden_spear") is True
    assert "wood" not in state.player.bag          # inputs consumed
    assert state.player.bag["wooden_spear"] == 1   # output produced
    assert state.player.pwr == 3                   # base PWR unchanged by crafting


def test_craft_fails_without_materials_and_changes_nothing():
    state = _state({"wood": 2})
    assert craft(state, "wooden_spear") is False
    assert state.player.bag == {"wood": 2}
    assert state.player.pwr == 3
