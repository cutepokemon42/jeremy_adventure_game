# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
import pytest

import storage
from models import Player, check_win


# --- check_win -------------------------------------------------------------

def test_reach_level_win():
    assert check_win(Player(level=5), {"type": "reach_level", "level": 5}) is True
    assert check_win(Player(level=6), {"type": "reach_level", "level": 5}) is True
    assert check_win(Player(level=4), {"type": "reach_level", "level": 5}) is False


def test_collect_item_win():
    win = {"type": "collect_item", "id": "crystal", "count": 3}
    assert check_win(Player(bag={"crystal": 3}), win) is True
    assert check_win(Player(bag={"crystal": 2}), win) is False
    assert check_win(Player(bag={}), win) is False


def test_empty_win_config_never_wins():
    assert check_win(Player(level=99), {}) is False


# --- win config validation -------------------------------------------------

def test_valid_win_configs_pass():
    items = {"crystal": {"name": "Crystal"}}
    storage.validate_data({}, items, {}, {}, {"type": "reach_level", "level": 5})
    storage.validate_data({}, items, {}, {}, {"type": "collect_item", "id": "crystal", "count": 2})


def test_unknown_win_type_raises():
    with pytest.raises(ValueError):
        storage.validate_data({}, {}, {}, {}, {"type": "summon_dragon"})


def test_collect_item_win_unknown_item_raises():
    with pytest.raises(ValueError):
        storage.validate_data({}, {}, {}, {}, {"type": "collect_item", "id": "ghost"})


def test_reach_level_bad_level_raises():
    with pytest.raises(ValueError):
        storage.validate_data({}, {}, {}, {}, {"type": "reach_level", "level": 0})
