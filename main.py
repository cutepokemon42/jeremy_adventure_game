# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Entry point: load data, load or start a game, run the menu loop.

Run with:  python3 main.py
"""
from pathlib import Path

import actions
import engine
import storage
from leveling import level_down
from models import GameState, effective_max_hp

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SAVE_PATH = ROOT / "saves" / "save1.json"


def build_actions(state: GameState):
    """Return (labels, handlers) for the current location. Travel / look screens
    are always present; Gather, Fight, and Craft appear only where they apply."""
    loc = state.world[state.player.location]
    labels = ["Travel", "Look at inventory", "Look at stats"]
    handlers = [actions.travel, actions.show_inventory, actions.show_stats]
    if loc["gather"]:
        labels.append("Gather")
        handlers.append(actions.gather_action)
    if loc["enemies"]:
        labels.append("Fight")
        handlers.append(actions.fight_action)
    if loc.get("dungeon") and loc["dungeon"] in state.dungeons:
        dungeon_name = state.dungeons[loc["dungeon"]]["name"]
        labels.append(f"Enter Dungeon ({dungeon_name})")
        if loc["dungeon"] == "labyrinth":
            handlers.append(actions.labyrinth_action)
        else:
            handlers.append(actions.dungeon_action)
    if state.recipes:
        labels.append("Craft")
        handlers.append(actions.craft_action)
    labels.append("Equip")
    handlers.append(actions.equip_action)
    labels.append("Use item")
    handlers.append(actions.use_item_action)
    labels.append("Save and quit")
    handlers.append(None)
    return labels, handlers


def _respawn(state: GameState) -> None:
    """Handle player death: level down, teleport to Spawn, restore HP."""
    p = state.player
    old_level = p.level
    level_down(p)
    p.location = "spawn"
    p.hp = effective_max_hp(p, state.items)
    print("\nYou fall in battle and wake at the Spawn, weaker than before.")
    if p.level < old_level:
        print(f"You dropped to level {p.level} (was {old_level}). "
              f"HP {p.hp}/{p.max_hp}, PWR {p.pwr}.")
    else:
        print(f"You lost some XP but remain level {p.level}.")


def _unlocks_at(old_level: int, new_level: int, state: GameState) -> list[str]:
    """Return display names of locations that just crossed into the reachable range."""
    names = []
    for loc in state.world.values():
        req = loc.get("min_level", 1)
        if old_level < req <= new_level:
            names.append(loc["name"])
    return names


def main() -> None:
    world, items, enemies, recipes, win, dungeons = storage.load_data(DATA_DIR)
    player = storage.load_or_new_game(SAVE_PATH, world, items)
    state = GameState(player=player, world=world, items=items,
                      enemies=enemies, recipes=recipes, win=win, dungeons=dungeons)

    print("Welcome to jeremy. Pick an action by typing its number.")
    while True:
        loc = state.world[state.player.location]
        print(f"\n== {loc['name']} ==")
        print(loc["description"])
        labels, handlers = build_actions(state)
        title = f"What do you do? (HP {state.player.hp}/{state.player.max_hp}, Lvl {state.player.level})"
        before_level = state.player.level
        handler = handlers[engine.menu(title, labels)]
        if handler is None:
            storage.save_game(SAVE_PATH, state.player)
            print("Saved. See you next time.")
            return
        result = handler(state)
        if result == "game_over":
            print("\nYour journey has ended. The Labyrinth claimed your soul.")
            print("Start a new game to try again.")
            storage.delete_save(SAVE_PATH)
            return
        if state.player.hp <= 0:
            _respawn(state)
        unlocked = _unlocks_at(before_level, state.player.level, state)
        if unlocked:
            print(f"New area unlocked: {', '.join(unlocked)}!")
        storage.save_game(SAVE_PATH, state.player)


if __name__ == "__main__":
    main()
