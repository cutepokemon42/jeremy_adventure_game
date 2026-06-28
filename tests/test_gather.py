# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from actions import gather
from models import GameState, Player


class MaxRng:
    """Deterministic rng stub: every roll returns the maximum of the range."""

    def randint(self, a, b):
        return b


def _mines_state():
    world = {
        "mines": {
            "name": "Mines", "description": "", "enemies": [],
            "gather": [
                {"kind": "item", "id": "stone", "min": 1, "max": 3},
                {"kind": "item", "id": "gold", "min": 0, "max": 1},
                {"kind": "xp", "min": 1, "max": 2},
            ],
        }
    }
    items = {
        "stone": {"name": "Stone", "type": "material"},
        "gold": {"name": "Gold", "type": "material", "xp_value": 5},
    }
    return GameState(player=Player(location="mines"), world=world, items=items)


def test_gather_stores_materials_smelts_gold_and_awards_xp():
    state = _mines_state()
    result = gather(state, rng=MaxRng())

    assert state.player.bag == {"stone": 3}      # stone stored
    assert "gold" not in state.player.bag        # gold never stored
    assert result["smelted"]["gold"] == (1, 5)   # 1 gold -> 5 XP
    assert result["xp"] == 5 + 2                 # gold 5 + xp entry max 2
    assert state.player.xp == 7
