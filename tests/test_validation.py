# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

import storage


def test_shipped_data_validates():
    root = Path(__file__).resolve().parent.parent
    storage.load_data(root / "data")  # must not raise


def test_unknown_gather_item_raises():
    world = {"spawn": {"name": "Spawn", "description": "", "enemies": [],
                       "gather": [{"kind": "item", "id": "ghost", "min": 1, "max": 1}]}}
    with pytest.raises(ValueError):
        storage.validate_data(world, {"wood": {}}, {}, {})


def test_unknown_enemy_raises():
    world = {"jungle": {"name": "Jungle", "description": "", "enemies": ["dragon"], "gather": []}}
    with pytest.raises(ValueError):
        storage.validate_data(world, {}, {}, {})


def test_unknown_recipe_item_raises():
    recipes = {"bad": {"name": "Bad", "requires": {"phantom": 1}, "creates": {"wood": 1}}}
    with pytest.raises(ValueError):
        storage.validate_data({}, {"wood": {}}, {}, recipes)
