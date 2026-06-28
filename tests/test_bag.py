# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from models import Player, add_item, has_items, remove_items


def test_add_item_accumulates():
    p = Player()
    add_item(p, "wood", 2)
    add_item(p, "wood", 3)
    assert p.bag["wood"] == 5


def test_add_item_ignores_nonpositive():
    p = Player()
    add_item(p, "wood", 0)
    add_item(p, "wood", -4)
    assert "wood" not in p.bag


def test_has_items():
    p = Player(bag={"wood": 3, "stone": 1})
    assert has_items(p, {"wood": 2})
    assert has_items(p, {"wood": 3, "stone": 1})
    assert not has_items(p, {"wood": 4})
    assert not has_items(p, {"iron": 1})


def test_remove_items_success_clears_empty_stacks():
    p = Player(bag={"wood": 3, "stone": 2})
    assert remove_items(p, {"wood": 3, "stone": 1}) is True
    assert "wood" not in p.bag
    assert p.bag["stone"] == 1


def test_remove_items_insufficient_leaves_bag_unchanged():
    p = Player(bag={"wood": 1})
    assert remove_items(p, {"wood": 2}) is False
    assert p.bag == {"wood": 1}
