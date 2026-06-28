# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
from leveling import apply_level, level_for_xp
from models import Player


def test_level_for_xp_thresholds():
    assert level_for_xp(0) == 1
    assert level_for_xp(9) == 1
    assert level_for_xp(10) == 2
    assert level_for_xp(25) == 3


def test_apply_level_bumps_stats_and_heals():
    p = Player(hp=5, max_hp=20, pwr=3, xp=20, level=1)
    apply_level(p)
    assert p.level == 3            # 20 XP -> level 3
    assert p.max_hp == 20 + 2 * 5  # +5 max HP per level gained
    assert p.pwr == 3 + 2          # +1 PWR per level gained
    assert p.hp == p.max_hp        # level-up heals to full


def test_apply_level_noop_below_threshold():
    p = Player(hp=10, max_hp=20, pwr=3, xp=5, level=1)
    apply_level(p)
    assert (p.level, p.max_hp, p.pwr, p.hp) == (1, 20, 3, 10)
