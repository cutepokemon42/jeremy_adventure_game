# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""JSON loading, fail-fast validation, and save/load of player state."""
import json
from dataclasses import asdict
from pathlib import Path

from models import Player


def _read_json(path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_data(data_dir) -> tuple[dict, dict, dict, dict, dict, dict]:
    """Load and validate all content. Raises ValueError on any unresolved id."""
    data_dir = Path(data_dir)
    world = _read_json(data_dir / "world.json")["locations"]
    items = _read_json(data_dir / "items.json")["items"]
    enemies = _read_json(data_dir / "enemies.json")["enemies"]
    recipes = _read_json(data_dir / "recipes.json")["recipes"]
    win = _read_json(data_dir / "game.json")["win"]
    dungeons = _read_json(data_dir / "dungeons.json")["dungeons"]
    validate_data(world, items, enemies, recipes, win, dungeons)
    return world, items, enemies, recipes, win, dungeons


_EQUIP_SLOTS = ("weapon", "armor")
_EQUIP_BONUS_KEYS = {"weapon": "pwr_bonus", "armor": "max_hp_bonus"}


def validate_data(world: dict, items: dict, enemies: dict, recipes: dict, win: dict | None = None, dungeons: dict | None = None) -> None:
    """Fail fast if any referenced id does not resolve. "xp" is the one allowed
    non-item gather kind."""
    for loc_id, loc in world.items():
        for entry in loc["gather"]:
            if entry["kind"] == "item" and entry["id"] not in items:
                raise ValueError(f"{loc_id}: gather references unknown item '{entry['id']}'")
            if entry["kind"] not in ("item", "xp"):
                raise ValueError(f"{loc_id}: unknown gather kind '{entry['kind']}'")
        for enemy_id in loc["enemies"]:
            if enemy_id not in enemies:
                raise ValueError(f"{loc_id}: references unknown enemy '{enemy_id}'")
        dungeon_id = loc.get("dungeon")
        if dungeon_id is not None and dungeons is not None and dungeon_id not in dungeons:
            raise ValueError(f"{loc_id}: references unknown dungeon '{dungeon_id}'")
        if "min_level" in loc and (not isinstance(loc["min_level"], int) or loc["min_level"] < 1):
            raise ValueError(f"{loc_id}: min_level must be a positive int")
    _ENEMY_TYPES = {"melee", "ranged"}
    for enemy_id, e in enemies.items():
        etype = e.get("type")
        if etype is not None and etype not in _ENEMY_TYPES:
            raise ValueError(f"enemy {enemy_id}: type must be melee or ranged, got '{etype}'")
        for drop in e.get("drops", []):
            if drop["id"] not in items:
                raise ValueError(f"enemy {enemy_id}: drop references unknown item '{drop['id']}'")
    for recipe_id, r in recipes.items():
        for item_id in {**r["requires"], **r["creates"]}:
            if item_id not in items:
                raise ValueError(f"recipe {recipe_id}: unknown item '{item_id}'")
    # Consumable effects and equipment blocks must be well-formed so the game
    # never silently does nothing when the player uses or equips an item.
    _ABILITY_KINDS = {"lifesteal", "chill", "thorns", "burn", "regen"}
    for item_id, item in items.items():
        if item.get("type") == "consumable":
            effect = item.get("effect", {})
            if effect.get("kind") != "heal":
                raise ValueError(f"item {item_id}: consumable has unknown effect kind '{effect.get('kind')}'")
            if not isinstance(effect.get("amount"), int) or effect["amount"] <= 0:
                raise ValueError(f"item {item_id}: consumable heal amount must be a positive int")
        equip = item.get("equip")
        if equip is not None:
            slot = equip.get("slot")
            if slot not in _EQUIP_SLOTS:
                raise ValueError(f"item {item_id}: equip slot must be one of {_EQUIP_SLOTS}, got '{slot}'")
            if not equip.get("level_scaled") and _EQUIP_BONUS_KEYS[slot] not in equip:
                raise ValueError(f"item {item_id}: {slot} equip must define '{_EQUIP_BONUS_KEYS[slot]}'"
                                 " or set level_scaled: true")
            wtype = equip.get("weapon_type")
            if wtype is not None and wtype not in ("melee", "ranged", "magic"):
                raise ValueError(f"item {item_id}: weapon_type must be melee/ranged/magic, got '{wtype}'")
            ability = equip.get("ability")
            if ability is not None and ability.get("kind") not in _ABILITY_KINDS:
                raise ValueError(f"item {item_id}: unknown ability kind '{ability.get('kind')}'")
    if dungeons:
        for dungeon_id, d in dungeons.items():
            for floor_enemy in d.get("floors", []):
                if floor_enemy not in enemies:
                    raise ValueError(f"dungeon {dungeon_id}: floor references unknown enemy '{floor_enemy}'")
            for reward_id in d.get("reward", []):
                if reward_id not in items:
                    raise ValueError(f"dungeon {dungeon_id}: reward references unknown item '{reward_id}'")
            if "min_level" in d and (not isinstance(d["min_level"], int) or d["min_level"] < 1):
                raise ValueError(f"dungeon {dungeon_id}: min_level must be a positive int")
    if win:
        _validate_win(win, items, enemies)


def _validate_win(win: dict, items: dict, enemies: dict) -> None:
    """A win config must name a supported type and resolve any ids it references."""
    win_type = win.get("type")
    if win_type == "reach_level":
        if not isinstance(win.get("level"), int) or win["level"] < 1:
            raise ValueError("win reach_level: 'level' must be a positive int")
    elif win_type == "collect_item":
        if win.get("id") not in items:
            raise ValueError(f"win collect_item: unknown item '{win.get('id')}'")
        if not isinstance(win.get("count", 1), int) or win.get("count", 1) < 1:
            raise ValueError("win collect_item: 'count' must be a positive int")
    else:
        raise ValueError(f"win: unknown win type '{win_type}'")


def save_game(path, player: Player) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"version": 1, "player": asdict(player)}, f, indent=2)


def delete_save(path) -> None:
    """Remove the save file if it exists (used when a run ends in a win)."""
    Path(path).unlink(missing_ok=True)


def load_game(path, world: dict, items: dict) -> Player | None:
    """Load a saved player, or None if no save exists. Refuses a save whose
    location or bag references content that no longer exists."""
    path = Path(path)
    if not path.exists():
        return None
    data = _read_json(path)["player"]
    data.setdefault("item_levels", {})   # graceful upgrade from saves without item_levels
    player = Player(**data)
    if player.location not in world:
        raise ValueError(f"save references unknown location '{player.location}'")
    for item_id in player.bag:
        if item_id not in items:
            raise ValueError(f"save bag references unknown item '{item_id}'")
    for slot in ("weapon", "armor"):
        equipped = getattr(player, slot)
        if equipped is not None and equipped not in items:
            raise ValueError(f"save {slot} references unknown item '{equipped}'")
    return player


def load_or_new_game(path, world: dict, items: dict) -> Player:
    return load_game(path, world, items) or Player()
