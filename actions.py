# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Player actions: travel, gather, fight, craft, and the look-at screens.

Rule logic (gather, craft) is split into pure functions that take an rng so they
test deterministically; the *_action wrappers handle prompting and printing.
"""
import random

import combat
import engine
from leveling import apply_level
from models import (
    GameState,
    add_item,
    effective_max_hp,
    effective_pwr,
    equip_item,
    has_items,
    remove_items,
    use_item,
)


def _item_name(state: GameState, item_id: str) -> str:
    return state.items.get(item_id, {}).get("name", item_id)


def _item_display(state: GameState, item_id: str) -> str:
    """Like _item_name but appends the item level for level-scaled equippables."""
    name = _item_name(state, item_id)
    lvl = state.player.item_levels.get(item_id)
    if lvl and state.items.get(item_id, {}).get("equip", {}).get("level_scaled"):
        return f"{name} (Lvl {lvl})"
    return name


def _roll_item_level(player, items: dict, item_id: str) -> int | None:
    """Roll a level for a level-scaled item based on player.pwr. Returns None for non-scaled."""
    if not items.get(item_id, {}).get("equip", {}).get("level_scaled"):
        return None
    lo = max(1, player.pwr - 2)
    hi = max(lo, player.pwr)
    return random.randint(lo, hi)


def _apply_item_level(player, items: dict, item_id: str) -> None:
    """Roll and store an item level, keeping the result only if it beats the current one."""
    lvl = _roll_item_level(player, items, item_id)
    if lvl is not None:
        player.item_levels[item_id] = max(player.item_levels.get(item_id, 0), lvl)


def _weapon_type(state: GameState) -> str:
    """Return 'melee', 'ranged', or 'magic' for the equipped weapon, defaulting to melee."""
    if not state.player.weapon:
        return "melee"
    return state.items.get(state.player.weapon, {}).get("equip", {}).get("weapon_type", "melee")


# --- look screens ----------------------------------------------------------

def show_stats(state: GameState) -> None:
    p = state.player
    eff_pwr = effective_pwr(p, state.items)
    eff_max_hp = effective_max_hp(p, state.items)
    print("\n-- Stats --")
    print(f"  HP:    {p.hp}/{eff_max_hp}")
    print(f"  PWR:   {eff_pwr}")
    print(f"  XP:    {p.xp}")
    print(f"  Level: {p.level}")
    weapon = _item_display(state, p.weapon) if p.weapon else "(none)"
    armor = _item_display(state, p.armor) if p.armor else "(none)"
    wtype = ""
    if p.weapon:
        wtype = f"  [{_weapon_type(state)}]"
    print(f"  Weapon: {weapon}{wtype}")
    print(f"  Armor:  {armor}")


def show_inventory(state: GameState) -> None:
    print("\n-- Inventory --")
    if not state.player.bag:
        print("  (empty)")
        return
    for item_id, n in state.player.bag.items():
        print(f"  {_item_display(state, item_id)}: {n}")


# --- travel ----------------------------------------------------------------

def travel(state: GameState) -> None:
    here = state.player.location
    player_level = state.player.level
    dests = [loc_id for loc_id in state.world if loc_id != here]
    labels = []
    for d in dests:
        loc = state.world[d]
        req = loc.get("min_level", 1)
        if req > player_level:
            labels.append(f"{loc['name']}  [LOCKED — requires level {req}]")
        else:
            labels.append(loc["name"])
    labels.append("Stay here")
    choice = engine.menu("Travel where?", labels)
    if choice == len(dests):
        return
    dest_id = dests[choice]
    req = state.world[dest_id].get("min_level", 1)
    if req > player_level:
        print(f"You can't go there yet. Reach level {req} first.")
        return
    state.player.location = dest_id
    print(f"You travel to {state.world[dest_id]['name']}.")


# --- gather ----------------------------------------------------------------

def gather(state: GameState, rng=random) -> dict:
    """Apply the current location's gather table. Items go to the bag; any item
    with an xp_value is smelted straight to XP (never stored). Returns a summary."""
    player = state.player
    loc = state.world[player.location]
    gained_items: dict[str, int] = {}
    smelted: dict[str, tuple[int, int]] = {}
    gained_xp = 0
    for entry in loc["gather"]:
        n = rng.randint(entry["min"], entry["max"])
        if n <= 0:
            continue
        if entry["kind"] == "xp":
            gained_xp += n
            continue
        item_id = entry["id"]
        xp_value = state.items[item_id].get("xp_value")
        if xp_value:
            gained_xp += n * xp_value
            prev = smelted.get(item_id, (0, 0))
            smelted[item_id] = (prev[0] + n, prev[1] + n * xp_value)
        else:
            add_item(player, item_id, n)
            gained_items[item_id] = gained_items.get(item_id, 0) + n
    if gained_xp:
        player.xp += gained_xp
        apply_level(player)
    return {"items": gained_items, "xp": gained_xp, "smelted": smelted}


def gather_action(state: GameState) -> None:
    before_level = state.player.level
    result = gather(state)
    parts = [f"{n} {_item_name(state, i)}" for i, n in result["items"].items()]
    if result["xp"]:
        parts.append(f"{result['xp']} XP")
    print("You gathered: " + ", ".join(parts) + "." if parts else "You found nothing this time.")
    for item_id, (count, xp) in result["smelted"].items():
        print(f"The {_item_name(state, item_id)} was smelted into {xp} XP.")
    if state.player.level > before_level:
        p = state.player
        print(f"Level up! Now level {p.level} (HP {p.hp}/{p.max_hp}, PWR {p.pwr}).")


# --- combat ----------------------------------------------------------------

def _consumables(state: GameState) -> list[str]:
    """Bag item ids that are usable consumables, in bag order."""
    return [i for i in state.player.bag if state.items.get(i, {}).get("type") == "consumable"]


def _player_dmg_mult(wtype: str, distance: str) -> float:
    """Damage multiplier for the player's attack based on weapon type and distance.

    Magic ignores distance. Melee is penalised at far range (60%). Ranged is
    penalised at close range (80%) but deals full damage at far range."""
    if wtype == "magic":
        return 1.0
    if wtype == "ranged":
        return 1.0 if distance == "far" else 0.8
    # melee
    return 1.0 if distance == "close" else 0.6


def _enemy_pwr_mult(wtype: str, distance: str, enemy_type: str) -> float:
    """Multiplier applied to enemy PWR for their retaliation this round.

    Ranged player at far range: kiting reduces enemy effectiveness (× 0.75).
    Ranged enemy forced to close range: disrupted aim (× 0.70).
    Magic ignores distance — no modifier from either source."""
    if wtype == "ranged" and distance == "far":
        return 0.75
    if enemy_type == "ranged" and distance == "close":
        return 0.70
    return 1.0


def _attack_label(state: GameState, distance: str = "close") -> str:
    """Label the Attack move, hinting at any distance penalty."""
    wtype = _weapon_type(state)
    mult = _player_dmg_mult(wtype, distance)
    penalty = f"  ({int(mult * 100)}% — {'melee at range' if wtype == 'melee' else 'ranged too close'})" if mult < 1.0 else ""
    if state.player.weapon:
        return f"Attack with {_item_name(state, state.player.weapon)}{penalty}"
    return f"Attack (unarmed){penalty}"


def _slot_ability(state: GameState, slot: str) -> dict:
    """Return the ability block for the item equipped in slot, or {}."""
    item_id = getattr(state.player, slot, None)
    if not item_id:
        return {}
    return state.items.get(item_id, {}).get("equip", {}).get("ability", {})


def _victory(state: GameState, enemy: dict) -> str:
    """Award XP and drops, roll item levels on equippable drops, return 'win'."""
    print(f"You defeated the {enemy['name']}!")
    before_level = state.player.level
    drops = combat.on_victory(state.player, enemy)
    print(f"Gained {enemy['xp']} XP.")
    if drops:
        for drop_id in drops:
            _apply_item_level(state.player, state.items, drop_id)
        got = ", ".join(f"{n} {_item_display(state, i)}" for i, n in drops.items())
        print(f"Loot: {got}.")
    if state.player.level > before_level:
        print(f"Level up! Now level {state.player.level}.")
    return "win"


def _fight_enemy(state: GameState, enemy_id: str, difficulty: dict | None = None) -> str:
    """Fight a single enemy. Returns 'win', 'lose', or 'flee'.

    Distance starts based on enemy type (ranged → FAR, melee → CLOSE) and can
    be changed with Rush in / Move back (spends the player's turn). Distance
    modifiers:
      Melee at FAR   — 60% player damage
      Ranged at CLOSE— 80% player damage; no kiting benefit
      Ranged at FAR  — 100% player damage; enemy 75% PWR (kiting)
      Ranged enemy at CLOSE — enemy 70% PWR (disrupted aim)
      Magic          — ignores distance entirely

    Enemies with speed > 1 attack that many times per round."""
    if difficulty:
        enemy = combat.spawn_dungeon_enemy(enemy_id, state.enemies, state.player, state.items, difficulty)
    else:
        enemy = combat.spawn_enemy(enemy_id, state.enemies)

    wtype = _weapon_type(state)
    enemy_def = state.enemies.get(enemy_id, {})
    enemy_type = enemy_def.get("type", "melee")
    enemy_speed = enemy_def.get("speed", 1)

    # Starting distance is set by the enemy's combat type
    distance = "far" if enemy_type == "ranged" else "close"

    speed_note = f", attacks ×{enemy_speed}" if enemy_speed > 1 else ""
    print(f"\nA {enemy['name']} [{enemy_type}] appears!"
          f" HP {enemy['hp']}, PWR {enemy['pwr']}{speed_note}")
    if distance == "far":
        print(f"  They keep their distance. [FAR]"
              + (" Rush in for full melee damage!" if wtype == "melee" else ""))
    else:
        print(f"  They charge at you. [CLOSE]"
              + (" Move back for full ranged effectiveness!" if wtype == "ranged" else ""))

    while True:
        eff_max_hp = effective_max_hp(state.player, state.items)
        a_ability = _slot_ability(state, "armor")

        # --- start-of-round effects ---
        if enemy.get("_burning"):
            burn_dmg = enemy["_burning"]
            enemy["hp"] -= burn_dmg
            print(f"The {enemy['name']} burns for {burn_dmg}!")
            if enemy["hp"] <= 0:
                return _victory(state, enemy)

        if a_ability.get("kind") == "regen":
            cap = effective_max_hp(state.player, state.items)
            gained = min(a_ability["amount"], cap - state.player.hp)
            if gained > 0:
                state.player.hp += gained
                print(f"You regenerate {gained} HP (HP {state.player.hp}/{cap}).")

        # --- player move menu ---
        dist_label = "CLOSE" if distance == "close" else "FAR  "
        moves = [(_attack_label(state, distance), "attack")]
        if _consumables(state):
            moves.append(("Use item", "use"))
        moves.append(("Defend (brace for a weaker hit)", "defend"))
        if wtype != "magic":
            if distance == "far":
                moves.append(("Rush in  (close the gap)", "rush_in"))
            else:
                moves.append(("Move back  (open the gap)", "move_back"))
        moves.append(("Flee", "flee"))

        choice = engine.menu(
            f"{enemy['name']} HP {max(enemy['hp'], 0)}/{enemy['max_hp']} | "
            f"You HP {state.player.hp}/{eff_max_hp} | {dist_label}",
            [label for label, _ in moves],
        )
        move = moves[choice][1]

        if move == "flee":
            print("You flee back to safety.")
            return "flee"

        guarded = False
        if move == "use":
            if not _use_item_menu(state):
                continue
        elif move == "defend":
            guarded = True
            print("You brace yourself, ready to soften the next blow.")
        elif move == "rush_in":
            distance = "close"
            print(f"You rush toward the {enemy['name']}! [Now CLOSE]")
        elif move == "move_back":
            distance = "far"
            print(f"You fall back from the {enemy['name']}! [Now FAR]")
        else:  # attack
            dmg_mult = _player_dmg_mult(wtype, distance)
            dmg = combat.player_attacks(state.player, enemy, state.items, dmg_mult)
            print(f"You hit the {enemy['name']} for {dmg}.")

            w_ability = _slot_ability(state, "weapon")
            if dmg > 0 and enemy["hp"] > 0:
                kind = w_ability.get("kind")
                if kind == "lifesteal":
                    heal = max(1, int(dmg * w_ability["ratio"]))
                    cap = effective_max_hp(state.player, state.items)
                    actual = min(heal, cap - state.player.hp)
                    if actual > 0:
                        state.player.hp += actual
                        print(f"Lifesteal restores {actual} HP (HP {state.player.hp}/{cap}).")
                elif kind == "chill":
                    enemy["_chilled"] = w_ability["amount"]
                    print(f"The {enemy['name']} is chilled! (-{w_ability['amount']} PWR this round)")
                elif kind == "burn":
                    if wtype == "magic" or not enemy.get("_burning"):
                        enemy["_burning"] = w_ability["damage"]
                        if not enemy.get("_burning_announced"):
                            print(f"The {enemy['name']} is set ablaze! ({w_ability['damage']} burn/round)")
                            enemy["_burning_announced"] = True

            if enemy["hp"] <= 0:
                return _victory(state, enemy)

        # --- enemy's turn: compute effective PWR (distance + chill) ---
        pwr_mult = _enemy_pwr_mult(wtype, distance, enemy_type)
        eff_pwr = max(1, int(enemy["pwr"] * pwr_mult))
        chill = enemy.pop("_chilled", 0)
        if chill:
            eff_pwr = max(1, eff_pwr - chill)
        if eff_pwr != enemy["pwr"]:
            reasons = []
            if pwr_mult < 1.0:
                reasons.append("kiting" if wtype == "ranged" else "disrupted")
            if chill:
                reasons.append("chilled")
            print(f"The {enemy['name']} attacks at {eff_pwr} PWR ({', '.join(reasons)}).")

        orig_pwr = enemy["pwr"]
        enemy["pwr"] = eff_pwr

        for attack_num in range(enemy_speed):
            if enemy["hp"] <= 0:
                break
            guard_this = guarded and attack_num == 0
            taken = combat.enemy_attacks(state.player, enemy, guarded=guard_this)
            label = "hits you" if attack_num == 0 else "strikes again"
            print(f"The {enemy['name']} {label} for {taken}.")

            if taken > 0 and a_ability.get("kind") == "thorns":
                thorns_dmg = a_ability["amount"]
                enemy["hp"] -= thorns_dmg
                print(f"Thorns deal {thorns_dmg} back to the {enemy['name']}.")
                if enemy["hp"] <= 0:
                    enemy["pwr"] = orig_pwr
                    return _victory(state, enemy)

            if state.player.hp <= 0:
                enemy["pwr"] = orig_pwr
                return "lose"

        enemy["pwr"] = orig_pwr


def fight_action(state: GameState) -> None:
    loc = state.world[state.player.location]
    _fight_enemy(state, random.choice(loc["enemies"]))


def dungeon_action(state: GameState) -> None:
    loc = state.world[state.player.location]
    dungeon = state.dungeons[loc["dungeon"]]
    req = dungeon.get("min_level", 1)
    if state.player.level < req:
        print(f"The dungeon entrance holds you back. You need level {req} to enter.")
        return
    floors = dungeon["floors"]
    difficulty = dungeon.get("difficulty") or None
    print(f"\n=== {dungeon['name']} ===")
    print(dungeon["description"])
    print(f"({len(floors)} floors)\n")
    for i, enemy_id in enumerate(floors, 1):
        print(f"-- Floor {i}/{len(floors)} --")
        result = _fight_enemy(state, enemy_id, difficulty=difficulty)
        if result == "lose":
            return  # main loop handles death
        if result == "flee":
            print("You escaped the dungeon.")
            return
        if i < len(floors):
            choice = engine.menu("Continue deeper?", ["Press on", "Retreat"])
            if choice == 1:
                print("You retreat from the dungeon.")
                return
    bonus = dungeon.get("bonus_xp", 0)
    print(f"\nDungeon cleared! You earn a bonus {bonus} XP.")
    state.player.xp += bonus
    before = state.player.level
    apply_level(state.player)
    if state.player.level > before:
        print(f"Level up! Now level {state.player.level}.")
    rewards = dungeon.get("reward", [])
    if rewards:
        for item_id in rewards:
            add_item(state.player, item_id, 1)
            _apply_item_level(state.player, state.items, item_id)
        names = ", ".join(_item_display(state, i) for i in rewards)
        print(f"You find: {names}!")


# --- crafting --------------------------------------------------------------

def craft(state: GameState, recipe_id: str) -> bool:
    """Consume a recipe's inputs and produce its output. Returns False (changing
    nothing) if the player lacks the materials. Rolls an item level for any
    level-scaled equippable created, keeping it only if it beats the current one."""
    recipe = state.recipes[recipe_id]
    if not remove_items(state.player, recipe["requires"]):
        return False
    for item_id, n in recipe["creates"].items():
        add_item(state.player, item_id, n)
        _apply_item_level(state.player, state.items, item_id)
    return True


def craft_action(state: GameState) -> None:
    if not state.recipes:
        print("You don't know any recipes yet.")
        return
    ids = list(state.recipes)
    labels = []
    for rid in ids:
        r = state.recipes[rid]
        req = ", ".join(f"{n} {_item_name(state, i)}" for i, n in r["requires"].items())
        affordable = "" if has_items(state.player, r["requires"]) else "  (missing materials)"
        labels.append(f"{r['name']} [{req}]{affordable}")
    labels.append("Cancel")
    choice = engine.menu("Craft what?", labels)
    if choice == len(ids):
        return
    rid = ids[choice]
    if craft(state, rid):
        created_id = next(iter(state.recipes[rid]["creates"]))
        print(f"You crafted {_item_display(state, created_id)}.")
    else:
        print("You don't have the materials for that.")


# --- use item --------------------------------------------------------------

def _use_item_menu(state: GameState) -> bool:
    """Prompt for a consumable and use it. Returns True if one was used (a turn
    was spent), False if the player had none or cancelled. Shared by the combat
    loop and the top-level Use item action."""
    ids = _consumables(state)
    if not ids:
        print("You have no usable items.")
        return False
    labels = [f"{_item_name(state, i)} x{state.player.bag[i]}" for i in ids] + ["Cancel"]
    choice = engine.menu("Use what?", labels)
    if choice == len(ids):
        return False
    result = use_item(state.player, ids[choice], state.items)
    if not result["ok"]:
        print("You can't use that.")
        return False
    name = _item_name(state, result["item_id"])
    if result["effect"] == "heal":
        print(f"You use the {name} and recover {result['healed']} HP "
              f"(HP {state.player.hp}/{effective_max_hp(state.player, state.items)}).")
    return True


def use_item_action(state: GameState) -> None:
    _use_item_menu(state)


# --- equip -----------------------------------------------------------------

def equip_action(state: GameState) -> None:
    ids = [i for i in state.player.bag if state.items.get(i, {}).get("equip")]
    if not ids:
        print("You have nothing to equip.")
        return
    labels = []
    for i in ids:
        equip = state.items[i]["equip"]
        slot = equip["slot"]
        if equip.get("level_scaled"):
            lvl = state.player.item_levels.get(i, 1)
            if slot == "weapon":
                detail = f"+{lvl} PWR"
            else:
                detail = f"+{lvl * 4} max HP"
        elif slot == "weapon":
            detail = f"+{equip.get('pwr_bonus', 0)} PWR"
        else:
            detail = f"+{equip.get('max_hp_bonus', 0)} max HP"
        wtype = equip.get("weapon_type", "")
        type_tag = f" [{wtype}]" if wtype else ""
        labels.append(f"{_item_display(state, i)} ({slot}{type_tag}, {detail})")
    labels.append("Cancel")
    choice = engine.menu("Equip what?", labels)
    if choice == len(ids):
        return
    result = equip_item(state.player, ids[choice], state.items)
    if not result["ok"]:
        print("You can't equip that.")
        return
    name = _item_name(state, result["item_id"])
    if result["previous"]:
        print(f"You equip the {name} and stow the {_item_name(state, result['previous'])}.")
    else:
        print(f"You equip the {name}.")
