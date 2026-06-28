# jeremy — Implementation Plan

This plan keeps the game simple first: Python owns the rules and menu flow, while JSON owns world content and saved player state. The goal is to make adding locations, items, enemies, and recipes a data edit instead of a new function.

## Simple First Version

Build milestones M1-M3 before adding combat or crafting:

- Start the player at `spawn`.
- Let the player travel between locations.
- Show stats and inventory.
- Gather resources from the current location.
- Convert gathered gold into XP.
- Recompute level from XP.

This gives a complete playable loop without the extra state complexity of combat, item use, or equipment.

## Resolved Decisions

- HP and Health are one stat. Use `hp` for current health and `max_hp` for maximum health.
- The first version is open-ended. The player gathers resources, gains XP, levels up, and later crafts better items. A formal win condition can be added after the core loop works.
- Mines are resource-only at first. Dungeon enemies belong in a later milestone after basic combat is implemented.
- Gold converts immediately to XP in the simple first version instead of staying in the bag.

## File Layout

```text
jeremy/
  main.py              # entry point                       -> SPEC §6 "game"
  engine.py            # menu loop and input helpers
  models.py            # Player, GameState, bag helpers     -> SPEC §6 "player"
  actions.py           # travel, gather, stats, inventory   -> SPEC §6 "actions"
  leveling.py          # XP -> level/stat bumps
  combat.py            # fight loop (M4)                    -> SPEC §6 "combat"
  storage.py           # JSON load/validate/save helpers    -> SPEC §6 "data"
  data/
    world.json         # locations and gather tables (incl. the deep_mine dungeon)
    items.json         # item definitions (materials, consumables, equippables)
    enemies.json       # enemy definitions (incl. deep-mine cave_bat / rock_golem)
    recipes.json       # crafting recipes
    game.json          # win condition config
  saves/
    save1.json
  tests/
    test_bag.py        # add/has/remove item helpers
    test_leveling.py   # level_for_xp / apply_level
    test_combat.py     # deterministic fight outcomes, weapon dmg, guarded_damage
    test_crafting.py   # recipe validate/consume/produce (no stat bump)
    test_items.py      # use_item / equip_item / effective stats
    test_win.py        # check_win + win-config validation
    test_storage_equipment.py  # item validation + equipment save round-trip
    test_gather.py     # gather table application
    test_validation.py # data reference validation
```

This flat layout is the chosen structure (settles SPEC §6's language-agnostic sketch — each module maps to a SPEC §6 concept as annotated). Standard library only; Python 3.11+; no third-party deps.

## Core Python State

```python
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
    weapon: str | None = None   # equipped weapon item id (or None)
    armor: str | None = None    # equipped armor item id (or None)


@dataclass
class GameState:
    player: Player
    world: dict
    items: dict
    enemies: dict = field(default_factory=dict)
    recipes: dict = field(default_factory=dict)
    win: dict = field(default_factory=dict)
```

`weapon` and `armor` are equipment slots holding the item id equipped in each slot (or `None`). Base `pwr`/`max_hp` are the unequipped stats; equipment bonuses are applied on top through `effective_pwr(player, items)` and `effective_max_hp(player, items)` so stats never double-count. Both fields round-trip through `dataclasses.asdict` in the save file, and `storage.load_game` refuses a save whose `weapon`/`armor` references an item that no longer exists.

The bag is a stack map: item id -> quantity. Keep item ids stable and lowercase, such as `wood`, `stone`, `iron`, and `gold`.

## JSON Content

### `data/world.json`

```json
{
  "locations": {
    "spawn": {
      "name": "Spawn",
      "description": "A safe camp with a cold fire pit.",
      "enemies": [],
      "gather": []
    },
    "forest": {
      "name": "Forest",
      "description": "Quiet trees, fallen branches, and old paths.",
      "enemies": [],
      "gather": [
        {"kind": "item", "id": "wood", "min": 1, "max": 3},
        {"kind": "xp", "min": 1, "max": 2}
      ]
    },
    "jungle": {
      "name": "Jungle",
      "description": "Dense leaves, animal tracks, and useful wood.",
      "enemies": ["boar", "snake"],
      "gather": [
        {"kind": "item", "id": "wood", "min": 1, "max": 2},
        {"kind": "xp", "min": 1, "max": 3}
      ]
    },
    "mines": {
      "name": "Mines",
      "description": "Dark tunnels with stone, ore, and loose gold.",
      "enemies": [],
      "gather": [
        {"kind": "item", "id": "stone", "min": 1, "max": 3},
        {"kind": "item", "id": "iron", "min": 0, "max": 2},
        {"kind": "item", "id": "gold", "min": 0, "max": 1}
      ]
    }
  }
}
```

### `data/items.json`

```json
{
  "items": {
    "wood": {"name": "Wood", "type": "material"},
    "gold": {"name": "Gold", "type": "material", "xp_value": 5},
    "healing_poultice": {"name": "Healing Poultice", "type": "consumable", "effect": {"kind": "heal", "amount": 12}},
    "iron_sword": {"name": "Iron Sword", "type": "craftable", "equip": {"slot": "weapon", "pwr_bonus": 3}},
    "leather_armor": {"name": "Leather Armor", "type": "craftable", "equip": {"slot": "armor", "max_hp_bonus": 10}}
  }
}
```

Item blocks the rules read:

- `xp_value` (materials): the item is smelted straight to XP on gather instead of being stored (e.g. `gold`, `crystal`).
- `type: "consumable"` + `effect`: a usable item. The only effect `kind` so far is `heal` with a positive integer `amount`; using it restores that many HP capped at effective max HP and consumes one from the bag. Handled by the pure `models.use_item(player, item_id, items) -> result`.
- `equip` (`{"slot": "weapon"|"armor", "pwr_bonus"|"max_hp_bonus": N}`): the item can be equipped into that slot. `weapon` requires `pwr_bonus`; `armor` requires `max_hp_bonus`. Handled by the pure `models.equip_item(player, item_id, items) -> result`, which moves the item onto the slot and returns the previously equipped item (if any) to the bag.

`storage.validate_data` fails fast on a malformed consumable effect (unknown kind or non-positive amount) or a malformed `equip` block (bad slot or missing bonus key).

### Save File

```json
{
  "version": 1,
  "player": {
    "hp": 20,
    "max_hp": 20,
    "pwr": 3,
    "xp": 0,
    "level": 1,
    "location": "spawn",
    "bag": {
      "wood": 2,
      "stone": 1
    }
  }
}
```

## Loading and Validation

`storage.py` loads the JSON content once at startup and validates it before the game runs. Validation fails fast with a clear error naming the offending id — no silent defaults, no half-broken world.

```python
def load_data(data_dir: str) -> tuple[dict, dict, dict, dict, dict]:
    world = _read_json(f"{data_dir}/world.json")["locations"]
    items = _read_json(f"{data_dir}/items.json")["items"]
    enemies = _read_json(f"{data_dir}/enemies.json")["enemies"]
    recipes = _read_json(f"{data_dir}/recipes.json")["recipes"]
    win = _read_json(f"{data_dir}/game.json")["win"]
    validate_data(world, items, enemies, recipes, win)
    return world, items, enemies, recipes, win
```

`validate_data` fails fast on any unresolved id. Beyond gather item ids, enemy ids, drop ids, and recipe input/output ids ("xp" is the one allowed non-item gather kind), it also validates:

- Consumable items: `effect.kind` must be `heal` and `effect.amount` a positive int.
- `equip` blocks: `slot` must be `weapon` or `armor`, and the matching bonus key (`pwr_bonus` for weapon, `max_hp_bonus` for armor) must be present.
- The win config: known type, positive `reach_level` level, and a resolvable `collect_item` id.

The save file is validated on load too: the saved `location` must exist in `world`, every bag id must exist in `items`, and any equipped `weapon`/`armor` id must exist in `items` — otherwise refuse to load rather than start from a broken save.

## Menu Flow

The main loop prints the current location, builds valid actions for that location, asks for a numbered choice, then dispatches to the matching action.

```text
== Forest ==
Quiet trees, fallen branches, and old paths.

1. Travel
2. Look at inventory
3. Look at stats
4. Gather

> 4
You gathered: 2 Wood, 1 XP.
```

Invalid input should re-prompt instead of crashing:

```text
Choose 1-4: x
Invalid choice.
Choose 1-4:
```

## Helper Functions

Start with a few boring helpers. They prevent rule code from spreading everywhere.

```python
def add_item(player: Player, item_id: str, quantity: int) -> None:
    if quantity <= 0:
        return
    player.bag[item_id] = player.bag.get(item_id, 0) + quantity


def has_items(player: Player, costs: dict[str, int]) -> bool:
    return all(player.bag.get(item_id, 0) >= qty for item_id, qty in costs.items())


def remove_items(player: Player, costs: dict[str, int]) -> bool:
    if not has_items(player, costs):
        return False
    for item_id, qty in costs.items():
        player.bag[item_id] -= qty
        if player.bag[item_id] <= 0:
            del player.bag[item_id]
    return True
```

## Leveling

Keep level derived from XP, not separately advanced by hand. This makes save files easier to repair.

```python
def level_for_xp(xp: int) -> int:
    return max(1, xp // 10 + 1)


def apply_level(player: Player) -> None:
    old_level = player.level
    new_level = level_for_xp(player.xp)
    if new_level <= old_level:
        return
    gained = new_level - old_level
    player.level = new_level
    player.max_hp += gained * 5
    player.pwr += gained
    player.hp = player.max_hp
```

## Gathering

Gathering reads the current location's `gather` table. Each entry rolls a random integer from `min` to `max`.

Rules:

- `kind: "item"` adds to the bag — except gold (see below).
- `kind: "xp"` adds XP directly.
- Gold never stays in the bag: on gather, any item carrying an `xp_value` is converted immediately to that many XP (per the Resolved Decisions). So gold is gathered, smelted to XP, and never appears in inventory.

Example gather result:

```text
You gathered: 2 Stone, 1 Gold.
The Gold was smelted into 5 XP.
```

## Combat Later

Add combat after travel/gather/save works.

### `data/enemies.json`

```json
{
  "enemies": {
    "boar": {
      "name": "Boar",
      "hp": 8,
      "pwr": 2,
      "xp": 4,
      "drops": [
        {"id": "hide", "chance": 0.5, "min": 1, "max": 1}
      ]
    },
    "snake": {
      "name": "Snake",
      "hp": 5,
      "pwr": 3,
      "xp": 5,
      "drops": [
        {"id": "venom", "chance": 0.25, "min": 1, "max": 1}
      ]
    }
  }
}
```

Combat state should be temporary, not saved unless saving mid-fight becomes a feature.

```python
@dataclass
class CombatState:
    enemy_id: str
    enemy_name: str
    enemy_hp: int
    enemy_pwr: int
```

## Crafting Later

### `data/recipes.json`

```json
{
  "recipes": {
    "wooden_spear": {
      "name": "Wooden Spear",
      "requires": {"wood": 3},
      "creates": {"wooden_spear": 1}
    },
    "iron_sword": {
      "name": "Iron Sword",
      "requires": {"wood": 1, "iron": 3},
      "creates": {"iron_sword": 1}
    },
    "leather_armor": {
      "name": "Leather Armor",
      "requires": {"hide": 2},
      "creates": {"leather_armor": 1}
    },
    "healing_poultice": {
      "name": "Healing Poultice",
      "requires": {"herb": 2},
      "creates": {"healing_poultice": 1}
    }
  }
}
```

Recipes no longer carry an `effects` block. `actions.craft` only consumes inputs and produces the output item; it never mutates stats. A crafted weapon/armor gains its power through the equip system, and a crafted consumable gains its effect from the item's `effect` block — so crafting two spears just yields two spears instead of permanently stacking PWR.

### Equipment and consumables (implemented)

The power of crafted gear lives on the item, not the recipe (see the `items.json` `equip` and consumable `effect` blocks above):

- `models.use_item(player, item_id, items) -> result` — pure. Consumes one consumable and applies its effect; healing is capped at `effective_max_hp`. Returns `{"ok": bool, ...}` (with `reason` on failure: `missing`, `not_consumable`, `no_effect`).
- `models.equip_item(player, item_id, items) -> result` — pure. Moves an equippable item from the bag onto its `weapon`/`armor` slot; the previously equipped item (if any) returns to the bag. Returns `{"ok": bool, "slot", "previous", ...}`.
- `models.effective_pwr(player, items)` / `models.effective_max_hp(player, items)` — base stat plus the equipped item's bonus. Combat and the stats screen read these, never the bare `pwr`/`max_hp`.

The interactive wrappers in `actions.py` are `use_item_action`, `equip_action`, and the shared `_use_item_menu` (reused by both the top-level Use item action and the in-combat Use item move). They do the prompting/printing; all rule math stays in the pure functions.

### `data/game.json` (win condition)

```json
{
  "win": {"type": "reach_level", "level": 5}
}
```

`models.check_win(player, win) -> bool` is pure. Supported `type`s: `reach_level` (`player.level >= level`) and `collect_item` (`bag holds >= count of id`). An empty/missing win config means the game is open-ended (never won). The main loop calls `check_win` after every action; on a win it prints a message, deletes the save (`storage.delete_save`), and ends the run. `storage.validate_data` validates the win config: it rejects an unknown win type, a non-positive `reach_level` level, and a `collect_item` referencing an unknown item id.

### Combat move menu (implemented)

`actions.fight_action` builds a per-round move menu each round, showing only the moves that apply:

- **Attack** — `combat.player_attacks(player, enemy, items)` deals `effective_pwr`. The label names the equipped weapon ("Attack with Iron Sword") or reads "Attack (unarmed)".
- **Use item** — shown only when the bag holds a consumable; routes through `_use_item_menu` (which calls `models.use_item`) and consumes the turn.
- **Defend** — sets a guard flag so the enemy's retaliation this round is reduced via the pure `combat.guarded_damage(enemy_pwr) -> int` (half, rounded up, floored at 1). Consumes the turn.
- **Flee** — leaves with no rewards.

After any move that consumes the turn (Attack, Use item, Defend), `combat.enemy_attacks(player, enemy, guarded=...)` retaliates if the enemy is still alive, then the loop checks for player death. All combat math stays pure in `combat.py`.

## Reasonable Items To Add Later

Materials:

- `wood`
- `stone`
- `iron`
- `gold`
- `hide`
- `fiber`
- `herb`
- `venom`
- `crystal`

Consumables:

- `healing_poultice`: restores HP outside combat first, later in combat.
- `stamina_leaf`: boosts next gather result.
- `smoke_bomb`: guarantees flee.

Craftables:

- `wooden_spear`: early weapon.
- `stone_axe`: better wood gathering.
- `pickaxe`: better mines gathering.
- `iron_sword`: stronger weapon.
- `leather_armor`: increases max HP.
- `torch`: unlocks deeper mine/dungeon later.

These are typical for this kind of adventure game and give the player short-term goals without requiring a complicated equipment system immediately.

## Implementation Order

1. Create `data/items.json` and `data/world.json`.
2. Create `models.py` with `Player` and `GameState`.
3. Create `storage.py` with JSON load/save and default save creation.
4. Create `engine.py` with numbered menu helpers.
5. Create `actions.py` for travel, stats, inventory, and gather.
6. Create `main.py` and make M1-M3 playable.
7. Add `enemies.json` and `combat.py`.
8. Add `recipes.json` and craft validation.
9. Add save/load from the main menu.

Keep every step playable before adding the next system.

## Testing

The rule logic lives in pure functions with no `print`/`input`, so it tests directly with `python3 -m pytest`. Keep combat deterministic first (no random damage) so outcomes are assertable; add variance only after the tests pass.

- `test_bag.py` — `add_item`/`has_items`/`remove_items`; removing more than held returns `False` and leaves the bag unchanged.
- `test_leveling.py` — `level_for_xp` thresholds and `apply_level` stat bumps (and that it heals to full on level-up).
- `test_combat.py` — fixed HP/PWR produce a known winner; victory awards XP and rolls drops; attack uses effective PWR with an equipped weapon; `guarded_damage` halves rounding up (floored at 1) and `enemy_attacks(guarded=True)` takes the reduced hit.
- `test_crafting.py` — a recipe succeeds only when all inputs are present, consumes exactly the inputs, produces the output, and does NOT bump stats (the PWR bump now comes from equipping).
- `test_items.py` — `use_item` heals/caps/consumes and fails cleanly on missing/non-consumable; `equip_item` sets the slot, swaps gear back to the bag, leaves base stats untouched, and fails on non-equippable; `effective_pwr`/`effective_max_hp` with and without gear.
- `test_win.py` — `check_win` for `reach_level`/`collect_item`/empty config, plus win-config validation (unknown type, unknown item, bad level).
- `test_storage_equipment.py` — malformed consumable/equip blocks raise from `validate_data`; Player `weapon`/`armor` round-trip through save/load; a save referencing an unknown equipped item is refused.

All new pure functions are tested with the deterministic rng stubs already in `tests/` (`MaxRng`, `AlwaysDropRng`, `NoDropRng`); no test uses real randomness.

Validation tests also cover a `world.json` referencing an unknown item or enemy id raising from `validate_data`.

## Audit Notes (from Codex)

### Problems To Fix Before Coding

- The simple first version says to build M1-M3 before combat, but the sample `world.json` gives `jungle` enemies `["boar", "snake"]`. If `enemies.json` is empty until M4, startup validation will fail immediately. Fix: either keep `jungle.enemies` empty for M1-M3, or create `enemies.json` in step 1 with `boar` and `snake` even though the fight action is disabled until M4.
- `load_data()` unconditionally reads `data/enemies.json` and `data/recipes.json`, but the file layout marks both as "later". Fix: create both files from the start with empty top-level maps (`{"enemies": {}}` and `{"recipes": {}}`), or make `storage.py` treat missing future files as empty only for those two known files.
- The implementation order says `storage.py` should create/load saves in step 3, then says "Add save/load from the main menu" in step 9. Fix: split this into two tasks: step 3 can load data files and create a new default in-memory `GameState`; save-file persistence and menu actions should move earlier if "travel/gather/save works" is a blocker for combat, or the Combat Later sentence should say "after travel/gather works" instead.
- The crafting examples create `wooden_spear`, `iron_sword`, and `pickaxe`, but `items.json` only defines raw materials. Validation will fail once `recipes.json` is added unless craftable output items are also added to `items.json`.
- The enemy examples drop `hide` and `venom`, but those items are only listed in "Reasonable Items To Add Later" and not in `items.json`. Validation will fail once `enemies.json` includes those drops unless `hide` and `venom` are added to `items.json` in the same milestone.
- Gold conversion is described as "any item carrying an `xp_value` is converted immediately to XP", not just gold. That is flexible, but it means an item can never be both inventory material and XP material. Fix: either keep that generic rule and document it as `xp_value` means "auto-convert on gather", or make the rule explicit to `gold` only.
- `level` is described as derived from XP, but the save file stores `level`. Fix: on save, storing level is fine for readability, but on load recompute `level`, `max_hp`, and `pwr` from XP or validate that the stored values match the derived values. Otherwise hand-edited saves can drift.
- The main menu does not include a `Quit` option. Without it, the player has to interrupt the program. Add `Quit` from the first playable version, and add `Save and quit` once persistence exists.
- The sample validation only checks missing references. It should also validate required keys, unknown gather kinds, non-integer quantities, negative quantities, `min <= max`, enemy HP/PWR > 0, XP >= 0, and drop chances in `[0.0, 1.0]`.

### Improvements

- Inject randomness instead of calling random functions directly inside actions. Pass an `rng` object into `gather()` and future combat/drop functions so tests can use a seeded or fake RNG.
- Keep `print`/`input` out of rule logic. `actions.py` should return structured results such as gathered items, XP gained, and level-up messages; `engine.py` should handle display. This matches the testing section and prevents menu text from becoming hard to test.
- Use `pathlib.Path` in `storage.py` instead of string paths like `f"{data_dir}/world.json"`. It avoids path bugs and keeps file handling cleaner.
- Add `GameState.enemies` and `GameState.recipes` now, even if they are empty for M1-M3. That keeps the state shape stable as features are added.
- Decide whether travel is fully open from every location or uses per-location exits. Fully open travel is easiest. If exits may become restricted later, add an `exits` list to `world.json` now so content stays data-driven.
- Add a small `new_game()` constructor that creates a valid `GameState` with a default `Player`. Avoid scattering default player creation through `main.py`, tests, and save loading.
- Make `remove_items()` reject negative costs during validation or inside the helper. A negative quantity would currently pass `has_items()` and then increase inventory when removed.
- For first crafting, prefer "crafted item has no effect yet" over permanent stat bumps. Permanent one-time bumps require tracking whether an effect was already applied; otherwise crafting two spears can accidentally stack PWR forever.
- Add a short death rule before implementing combat: after player HP reaches 0, either reset to Spawn with full HP and lose some XP/items, or end the run and require loading a save. Combat code needs this decision.
- Add smoke-test instructions once code exists: run the game, choose travel to Forest, gather once, view inventory/stats, quit. That catches broken menu wiring faster than unit tests alone.
