# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Runtime state (Player, GameState) and the bag helper functions.

These are pure data + pure functions, no I/O, so they unit-test directly.
"""
from dataclasses import dataclass, field


@dataclass
class Player:
    hp: int = 20
    max_hp: int = 20
    pwr: int = 3
    xp: int = 0
    level: int = 1
    location: str = "spawn"
    bag: dict[str, int] = field(default_factory=dict)
    # Equipment slots: the item id equipped in each slot, or None.
    weapon: str | None = None
    armor: str | None = None
    # Per-item level for level-scaled equipment, rolled when the item is obtained.
    # Unique/fixed items are not in this dict; their bonus is read from items data.
    item_levels: dict[str, int] = field(default_factory=dict)
    # Mana system for magic spells
    mana: int = 100
    max_mana: int = 100


@dataclass
class GameState:
    player: Player
    world: dict
    items: dict
    enemies: dict = field(default_factory=dict)
    recipes: dict = field(default_factory=dict)
    win: dict = field(default_factory=dict)
    dungeons: dict = field(default_factory=dict)


def effective_pwr(player: Player, items: dict) -> int:
    """Base PWR plus the equipped weapon's bonus.

    Level-scaled weapons use the rolled item level stored in player.item_levels
    directly as the PWR bonus (so a level-3 sword gives +3 PWR). Fixed-bonus
    unique items use the pwr_bonus field from items data."""
    if not player.weapon:
        return player.pwr
    equip = items.get(player.weapon, {}).get("equip", {})
    if equip.get("level_scaled"):
        bonus = player.item_levels.get(player.weapon, 1)
    else:
        bonus = equip.get("pwr_bonus", 0)
    return player.pwr + bonus


def effective_max_hp(player: Player, items: dict) -> int:
    """Base max HP plus the equipped armor's bonus.

    Level-scaled armors give item_level * 4 max HP. Fixed-bonus unique items
    use the max_hp_bonus field from items data."""
    if not player.armor:
        return player.max_hp
    equip = items.get(player.armor, {}).get("equip", {})
    if equip.get("level_scaled"):
        bonus = player.item_levels.get(player.armor, 1) * 4
    else:
        bonus = equip.get("max_hp_bonus", 0)
    return player.max_hp + bonus


def check_win(player: Player, win: dict) -> bool:
    """True if the player has met the data-driven win condition. Pure: no I/O.

    Supported win types (from data/game.json):
      - {"type": "reach_level", "level": N}      -> player.level >= N
      - {"type": "collect_item", "id": X, "count": N} -> bag holds >= N of X
    An empty/missing win config means the game is open-ended (never won)."""
    win_type = win.get("type")
    if win_type == "reach_level":
        return player.level >= win["level"]
    if win_type == "collect_item":
        return player.bag.get(win["id"], 0) >= win.get("count", 1)
    return False


def use_item(player: Player, item_id: str, items: dict) -> dict:
    """Use one consumable from the bag and apply its effect. Pure: no I/O.

    Returns a result dict: {"ok": bool, "reason"/"effect"/"healed"/... }.
    Currently the only effect kind is "heal" (restore HP based on ratio of
    effective max HP). Fails (ok=False) if the item is missing, not a consumable,
    or has no usable effect. On success the item is consumed.
    """
    if player.bag.get(item_id, 0) <= 0:
        return {"ok": False, "reason": "missing", "item_id": item_id}
    definition = items.get(item_id, {})
    if definition.get("type") != "consumable":
        return {"ok": False, "reason": "not_consumable", "item_id": item_id}
    effect = definition.get("effect", {})
    if effect.get("kind") != "heal":
        return {"ok": False, "reason": "no_effect", "item_id": item_id}
    cap = effective_max_hp(player, items)
    ratio = effect.get("ratio", 0)
    amount = max(1, int(cap * ratio))
    before = player.hp
    player.hp = min(cap, player.hp + amount)
    healed = player.hp - before
    remove_items(player, {item_id: 1})
    return {"ok": True, "effect": "heal", "item_id": item_id, "healed": healed, "hp": player.hp}


def equip_item(player: Player, item_id: str, items: dict) -> dict:
    """Equip an item into its slot (weapon/armor). Pure: no I/O.

    Equipment must be in the bag and carry an "equip" block naming a slot. The
    previously equipped item (if any) returns to the bag, so swapping never loses
    gear. Returns {"ok": bool, ...}.
    """
    if player.bag.get(item_id, 0) <= 0:
        return {"ok": False, "reason": "missing", "item_id": item_id}
    equip = items.get(item_id, {}).get("equip")
    if not equip or "slot" not in equip:
        return {"ok": False, "reason": "not_equippable", "item_id": item_id}
    slot = equip["slot"]
    if slot not in ("weapon", "armor"):
        return {"ok": False, "reason": "bad_slot", "slot": slot}
    previous = getattr(player, slot)
    remove_items(player, {item_id: 1})
    if previous:
        add_item(player, previous, 1)
    setattr(player, slot, item_id)
    # Equipping armor can raise effective max HP; never lower current HP, and
    # leave current HP where it is (the bonus is headroom, not instant healing).
    return {"ok": True, "slot": slot, "item_id": item_id, "previous": previous}


def add_item(player: Player, item_id: str, quantity: int = 1) -> None:
    """Add quantity of item_id to the bag. Non-positive quantities are ignored."""
    if quantity <= 0:
        return
    player.bag[item_id] = player.bag.get(item_id, 0) + quantity


def has_items(player: Player, costs: dict[str, int]) -> bool:
    """True only if the bag holds at least every (item, qty) pair in costs."""
    return all(player.bag.get(item_id, 0) >= qty for item_id, qty in costs.items())


def remove_items(player: Player, costs: dict[str, int]) -> bool:
    """Remove costs from the bag. Returns False (and changes nothing) if short."""
    if not has_items(player, costs):
        return False
    for item_id, qty in costs.items():
        player.bag[item_id] -= qty
        if player.bag[item_id] <= 0:
            del player.bag[item_id]
    return True
