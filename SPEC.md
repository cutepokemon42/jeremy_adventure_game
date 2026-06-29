# jeremy — Spec

A single-player, text-based adventure game available in **two versions**:
- **Text-based CLI** (Python) — the original command-line interface
- **Web-based GUI** (HTML, CSS, and JavaScript) — visual 2D top-down exploration and combat

The player travels between locations, gathers and crafts materials, fights enemies, and gains XP.
All interaction is menu-driven. There is no win condition — new and harder content
unlocks as the player levels up.

## Implementations

### Python CLI (Original)
- Pure Python with JSON data files
- Text menu interface with numbered choices
- Run with `python3 main.py` from the repository root
- All core logic: combat, leveling, crafting, abilities, item levels

### Browser GUI (Visual)
- Dependency-free JavaScript port of the core Python game systems
- Visual 2D top-down overworld based on the original Jeremy concept art
- Turn-based combat with distance, equipment abilities, and animations
- Shared JSON content from `data/` for world, enemies, items, recipes, and dungeons
- LocalStorage auto-save/load
- Number keys 1–9 select visible actions; Escape closes menus
- Run `python3 -m http.server 8000`, then open `/docs/` in a browser

---

## 1. Player

| Stat | Description |
|------|-------------|
| **HP** | Current health (`hp`). Drops in combat; death at 0. |
| **max HP** | Maximum health (`max_hp`). Increases on level-up and via armor. |
| **PWR** | Base attack power. Increases on level-up and via equipped weapons. |
| **XP** | Earned from combat and gathering. Every 10 XP = one level. |
| **Level** | Derived from XP. Each level gained: +5 max HP, +1 PWR, full heal. |
| **Bag** | Inventory: item_id → quantity. |
| **Weapon slot** | One equipped weapon (or none). |
| **Armor slot** | One equipped armor piece (or none). |
| **Item levels** | Per-item level for craftable gear, rolled on obtain (see §6). |

Base stats never include equipment bonuses. Effective PWR and effective max HP
are always computed on the fly so equipping or swapping gear never double-counts.

---

## 2. World

Seven locations. Locked locations appear in the travel menu but cannot be
entered below their required level.

| Location | Min level | Enemies | Gatherables | Dungeon |
|----------|-----------|---------|-------------|---------|
| Spawn | — | — | — | — |
| Forest | — | — | wood, herb, XP | — |
| Jungle | — | boar, snake | wood, herb, XP | Bandit Den |
| Mines | — | — | stone, iron, gold | Deep Mine Dungeon |
| Deep Mine | — | cave bat, rock golem | stone, iron, crystal | — |
| Volcano | 3 | lava lizard, fire drake | volcanic stone, ember | Molten Core |
| Shadow Ruins | 5 | shade walker, bone knight | shadow essence, bone | Crypt of the Damned |

Gold and ember and shadow essence carry an `xp_value` and are smelted into XP
on gather instead of entering the bag. Crystal does the same.

---

## 3. Enemies

| Enemy | Type | HP | PWR | XP | Location | Drops |
|-------|------|----|-----|----|----------|-------|
| Boar | Melee | 8 | 2 | 4 | Jungle | hide (50%), **Shadow Blade (5%)**, **Shadow Cloak (4%)** |
| Snake | **Ranged** | 5 | 3 | 5 | Jungle | venom (25%), **Viper Shot (5%)**, **Blood Robe (4%)** |
| Cave Bat | Melee | 6 | 3 | 6 | Deep Mine | hide (40%), **Phantom Bow (4%)**, **Berserker Hide (4%)** |
| Rock Golem | Melee | 20 | 5 | 15 | Deep Mine | crystal (60%), iron (50%), **Ancient Sword (4%)**, **Ancient Guard (3%)** |
| Lava Lizard | Melee | 14 | 5 | 8 | Volcano | drake scale (35%), **Iron Will (4%)**, **Ember Plate (3%)** |
| Fire Drake | **Ranged** | 22 | 7 | 16 | Volcano | drake scale (55%), ember (40%), **Soul Staff (4%)**, **Void Shroud (3%)** |
| Shade Walker | Melee | 18 | 7 | 13 | Shadow Ruins | shadow essence (45%), **Shadow Fury (4%)**, **Shadow Cloak (4%)** |
| Bone Knight | Melee | 30 | 9 | 22 | Shadow Ruins | bone (60%), **Dark Claymore (3%)**, **Bone Plate (3%)** |
| Shadow Archer | **Ranged** | 15 | 8 | 16 | Shadow Ruins | shadow essence (50%), bone (30%), **Death Arrow (4%)**, **Guardian Plate (3%)** |

**Type** — determines starting distance and aim disruption (see §7 Combat).
Ranged enemies open at FAR; melee enemies open at CLOSE.

**World scaling** — non-dungeon enemies scale with player level.
Scaling factor: `1.0 + max(0, level - 2) × 0.15`. Enemy HP and PWR are scaled
up to a minimum of their base stats; this keeps difficulty smooth as the player
levels while never making early enemies easier.

**Unique drops** — most enemies now carry 2 rare unique weapon/armor drops
(shown in bold above). These are powerful items with special abilities and
provide build variety throughout the game.

**Dungeon scaling** — when spawned inside a dungeon, enemy HP and PWR are
scaled relative to the player's current effective stats using the dungeon's
`difficulty` ratios (see §5). Dungeon scaling overrides world scaling;
base stats are the floor.

---

## 4. Items (80 total)

### Materials (13)
Raw resources. Cannot be equipped. Some carry an `xp_value` and are smelted
to XP automatically on gather.

Wood, Stone, Iron, Hide, Venom, Herb, Bone, Drake Scale, Volcanic Stone
(no XP value); **Gold** (5 XP), **Crystal** (8 XP), **Ember** (10 XP),
**Shadow Essence** (15 XP).

### Consumables (6)
Used from the bag for an immediate effect. One is consumed per use.

| Item | Healing |
|------|---------|
| Healing Poultice | 12 HP |
| **Strong Poultice** | **25 HP** |
| **Greater Poultice** | **40 HP** |
| **Elixir of Life** | **60 HP** |
| **Blood Draught** | **20 HP** |
| **War Tonic** | **15 HP** |

### Craftable gear (12, level-scaled)
Crafted from materials. Each piece has a **level** rolled on craft (see §6).
Level-scaled weapons and armor never have fixed stat bonuses; the level itself
is the bonus.

**Base weapons/armor:**
- Wooden Spear (Ranged, Wood ×3)
- Hunter's Bow (Ranged, Wood ×4 + Hide ×2)
- Iron Sword (Melee, Wood ×1 + Iron ×3)
- Bone Blade (Melee, Bone ×3)
- Leather Armor (Hide ×2)
- Drake Armor (Volcanic Stone ×2 + Drake Scale ×2)

**Ability-based weapons/armor:**
- **Venom Spear** (Ranged, poison ability, Wood ×3 + Venom ×2)
- **Swift Longbow** (Ranged, swift ability, Wood ×4 + Crystal ×2)
- **Berserker Club** (Melee, berserker ability, Stone ×3 + Hide ×2)
- **Poison Dagger** (Melee, poison ability, Iron ×2 + Venom ×1)
- **Mark Blade** (Melee, mark ability, Iron ×4 + Shadow Essence ×1)
- **Shield Plate** (Armor, shield ability, Stone ×4 + Iron ×2)

### Unique gear (49)

**Dungeon reward items (5)** — fixed stats, awarded only by clearing dungeons:
- **Jade Fang** (Melee weapon, +4 PWR, lifesteal)
- **Ice Scythe** (Magic weapon, +6 PWR, chill)
- **Crystal Shield** (Armor, +18 max HP, thorns)
- **Flame Blade** (Magic weapon, +8 PWR, burn)
- **Void Cloak** (Armor, +22 max HP, regen)

**Enemy drops (44)** — rare 3–5% drops from world enemies, include powerful
weapons and armor with custom abilities:

| Weapon type | Count | Examples |
|---|---|---|
| Melee weapons | 15 | Shadow Blade (+7, execute), Berserker Axe (+7, berserker), Vampire Sword (+6, lifesteal), etc. |
| Ranged weapons | 8 | Phantom Bow (+6, swift), Viper Shot (+5, poison), Death Arrow (+9, execute), etc. |
| Magic weapons | 6 | Soul Staff (+7, burn), Venom Wand (+6, poison), Life Drain (+5, lifesteal), etc. |
| Armor | 15 | Shadow Cloak (+15, shield), Ancient Guard (+20, shield), Vampire Robe (+14, regen), etc. |

### Weapon types

| Type | Damage | Enemy retaliation | Ability trigger |
|------|--------|-------------------|-----------------|
| Melee | 100% | Full PWR | First application only |
| Ranged | 80% | 75% PWR (kiting) | First application only |
| Magic | 100% | Full PWR | Re-applies every hit |

### Abilities

| Ability | Slot | Effect |
|---------|------|--------|
| Lifesteal | Weapon | Restores HP equal to `ratio × damage` dealt each hit |
| Chill | Weapon | Reduces enemy PWR by `amount` for the rest of that round |
| Burn | Weapon | Sets enemy ablaze; they take `damage` at the start of each round |
| Thorns | Armor | Reflects `amount` damage back to the attacker on every hit taken |
| Regen | Armor | Restores `amount` HP at the start of each round |

---

## 4b. Abilities (12 types)

**Weapon offensive abilities:**

| Ability | Trigger | Effect |
|---------|---------|--------|
| **Lifesteal** | Every hit | Restore HP equal to `ratio × damage` (e.g., 40% lifesteal on 50 dmg = 20 HP) |
| **Chill** | Every hit | Reduce enemy PWR by `amount` for the rest of this round only |
| **Burn** | First hit (melee/ranged) or every hit (magic) | Deal `damage` to enemy HP at start of each round until death |
| **Execute** | Every hit | If enemy HP < `threshold × max_hp`, multiply your damage by `bonus` (e.g., execute when <30% HP deals 50% more) |
| **Poison** | First hit or every hit (magic) | Deal `damage` to enemy HP per round for `ticks` rounds. Applies once unless magic weapon. |
| **Mark** | First hit | First hit marks enemy. All subsequent hits deal `bonus_mult × 100` damage (e.g., 1.2 = +20%). Persists until enemy dies. |
| **Swift** | Always | Ignore distance penalties; always deal 100% weapon damage (CLOSE or FAR) |

**Armor defensive abilities:**

| Ability | Trigger | Effect |
|---------|---------|--------|
| **Regen** | Start of round | Restore `amount` HP per round (capped at effective max HP) |
| **Thorns** | After being hit | Reflect `amount` damage back to attacker; kills enemy if damage exceeds their remaining HP |
| **Shield** | After being hit | Reduce damage from that hit by up to `amount` (minimum 1 damage). Activates automatically. |
| **Fortify** | When HP < 30% max and hit | Reduce that hit's damage by 50% (rounded down, minimum 1). Invisible passive. |

---

## 5. Dungeons

Dungeons are a fixed sequence of enemies fought one after another. After each
floor the player can retreat or press on. Dying or fleeing in a dungeon exits
immediately with no rewards. Clearing all floors awards bonus XP and unique
items.

| Dungeon | Location | Min level | Floors | Difficulty | Bonus XP | Reward |
|---------|----------|-----------|--------|------------|----------|--------|
| Bandit Den | Jungle | — | snake → boar → boar | 0.9× HP / 0.7× PWR | 10 | **Jade Fang, Vampire Sword, Vampire Robe** |
| Deep Mine Dungeon | Mines | 2 | bat → bat → rock golem | 1.3× HP / 0.9× PWR | 25 | **Ice Scythe, Crystal Shield, Berserker Axe, Iron Fortress** |
| Molten Core | Volcano | 3 | lizard → drake → drake | 1.2× HP / 0.95× PWR | 35 | **Flame Blade, Death Lance, Void Shroud** |
| Crypt of the Damned | Shadow Ruins | 5 | shade → archer → knight → shade → archer → knight | 1.5× HP / 1.0× PWR | 60 | **Void Cloak, Void Reaper, Dark Claymore, Shadow Fortress** |

Difficulty ratios are multiplied by the player's effective max HP and effective
PWR at the time the enemy spawns. The base stat is the floor.

---

## 6. Item Levels

Every craftable equippable has a **level** that is rolled when the item is first
obtained (crafted, enemy drop, or dungeon reward).

- **Roll range**: `max(1, player.pwr − 2)` to `player.pwr` at moment of obtaining.
- If the same item is obtained again with a higher roll, the stored level is
  upgraded. Lower rolls are discarded.
- **Weapon**: item level = PWR bonus (level 4 → +4 PWR).
- **Armor**: item level × 4 = max HP bonus (level 4 → +16 max HP).
- Unique items are not level-scaled and do not have item levels.
- Item levels are shown everywhere the item appears (inventory, stats, equip menu, loot).

---

## 7. Combat loop

### Starting distance

When a fight begins the distance is set by the **enemy's type**:
- Melee enemy → **CLOSE** (they rush you)
- Ranged enemy → **FAR** (they keep their distance)

Distance persists between rounds and is shown in the status header each round.

### Distance modifier table

| Player weapon | Distance | Player damage | Enemy PWR |
|---------------|----------|--------------|-----------|
| Melee | CLOSE | 100% | 100% |
| Melee | FAR | **60%** | 100% |
| Ranged | CLOSE | **80%** | 100% (no kiting) |
| Ranged | FAR | 100% | **75%** (kiting) |
| Magic | either | 100% | 100% |

Additionally, **ranged enemies at CLOSE** fire at **70% of their PWR** (disrupted aim),
regardless of player weapon type.

These modifiers stack with chill reductions.

### Round sequence

1. **Start of round**
   - If enemy is burning: deal burn damage. If this kills it, victory.
   - If player has regen armor: restore HP.

2. **Player's turn** — choose one:
   - **Attack** — deals effective PWR × distance modifier. The menu label shows
     the penalty percentage when the current distance is unfavourable. Weapon
     abilities apply or re-apply on a successful hit (see §4).
   - **Use item** — consume one consumable. Turn spent.
   - **Defend** — guard flag set; next enemy hit is `ceil(pwr/2)`, floored at 1.
   - **Rush in** — change distance FAR → CLOSE. Turn spent; no attack. (Hidden for magic weapons.)
   - **Move back** — change distance CLOSE → FAR. Turn spent; no attack. (Hidden for magic weapons.)
   - **Flee** — exit with no rewards.

3. **Enemy's turn** — single attack:
   - Apply distance modifier (kiting or disrupted aim, whichever applies).
   - Apply chill reduction if active.
   - Enemy attacks once. Guard reduces damage to `ceil(pwr/2)`, floored at 1.
   - Apply shield or fortify armor reductions after the hit (if applicable).
   - If player has thorns armor: reflect `amount` damage. If this kills the enemy, victory.
   - If player HP ≤ 0: respawn (see §11).

4. Repeat from step 1.

### Ability notes

**Poison ticks:** Damage is applied at the start of the round, before the player
moves. A poisoned enemy loses `damage` HP per round for `ticks` rounds. Once
the ticks expire, the poison clears.

**Marked damage:** Once marked, every subsequent hit against that enemy deals
bonus damage. The mark indicator persists visibly in the status line until the
enemy dies. Multiple weapon hits can extend the mark, but only one mark per
enemy exists.

**Execute threshold:** If an enemy is below the threshold (e.g., 30% HP), the
next successful hit applies the execute bonus. This resets each round so low-HP
enemies are always vulnerable to execution.

**Shield vs Fortify:** Shield is a flat reduction (up to `amount`); fortify only
triggers at low HP and halves the incoming damage. Both apply after the hit lands,
reducing the damage you take to match the displayed message.

---

## 8. Player actions

From any location:

| Action | Always shown? | Condition |
|--------|---------------|-----------|
| Travel | Yes | — |
| Look at inventory | Yes | — |
| Look at stats | Yes | — |
| Gather | When location has resources | forest, jungle, mines, deep mine, volcano, shadow ruins |
| Fight | When location has enemies | jungle, deep mine, volcano, shadow ruins |
| Enter Dungeon | When location has a dungeon and player meets min level | jungle, mines, volcano, shadow ruins |
| Craft | When any recipes are loaded | always (recipes are always loaded) |
| Equip | Yes | — |
| Use item | Yes | — |
| Save and quit | Yes | — |

Travel shows all destinations. Locked locations display `[LOCKED — requires
level N]` and cannot be entered until the requirement is met. Reaching a new
level announces any newly accessible areas.

---

## 9. Progression

The game is open-ended with no win condition. New locations and dungeons unlock
automatically as the player levels up:

| Level | Unlocks |
|-------|---------|
| 1 | Jungle, Bandit Den (→ Jade Fang) |
| 2 | Deep Mine Dungeon (→ Ice Scythe, Crystal Shield) |
| 3 | Volcano, Molten Core dungeon (→ Flame Blade) |
| 5 | Shadow Ruins, Crypt of the Damned (→ Void Cloak) |

Dungeon enemies scale with player stats, so cleared dungeons remain
challenging when revisited at a higher level.

---

## 10. Data files

| File | Contents |
|------|----------|
| `data/world.json` | Locations: name, description, enemies, gather table, dungeon id, min_level |
| `data/enemies.json` | Enemies: name, hp, pwr, speed, xp, drop table |
| `data/items.json` | Items: name, type, equip block (slot, weapon_type, level_scaled, pwr_bonus, ability), consumable effect |
| `data/recipes.json` | Recipes: name, requires, creates |
| `data/dungeons.json` | Dungeons: name, description, min_level, floors, difficulty, bonus_xp, reward |
| `data/game.json` | Win config (empty = open-ended) |
| `saves/save1.json` | Player state: all fields including bag, equipment slots, item_levels |

Adding a new location, enemy, item, or dungeon is a data edit only — no code
changes required as long as all referenced ids already exist.

---

## 11. File layout

```
jeremy_adventure_game/
  main.py       — entry point, main game loop, unlock announcements
  engine.py     — numbered menu, input re-prompting
  models.py     — Player, GameState, bag helpers, effective stat functions, check_win
  actions.py    — all player actions: travel, gather, fight, dungeon, craft, equip, use item
  combat.py     — pure combat math: spawn_enemy, spawn_dungeon_enemy, player_attacks, enemy_attacks, on_victory
  leveling.py   — level_for_xp, apply_level
  storage.py    — load_data, validate_data, save_game, load_game
  data/         — JSON content files (see §10)
  saves/        — save files
  tests/        — pytest test suite
```

Python 3.11+, standard library only.

---

## 11. Death and respawn

Dying does not end the run. Instead:

1. The player loses one level (minimum level 1). XP is set to the start of
   the new lower level; base `max_hp` and `pwr` are recalculated from scratch.
2. The player is teleported to **Spawn** with HP fully restored (including any
   armor bonus).
3. Equipment and bag contents are kept — only the level (and derived base
   stats) is penalised.

At level 1 death, XP resets to 0 but the level stays at 1.

The save file is written immediately after respawn so the penalty persists
even if the player quits.

## 12. Resolved decisions

- `hp` = current health, `max_hp` = maximum health. HP and Health are the same stat.
- Equipment bonuses are never baked into base `pwr`/`max_hp`. All effective stats are computed on the fly.
- Craftable gear uses level-scaled bonuses; unique gear uses fixed bonuses. The two systems never mix on the same item.
- Gold, crystal, ember, and shadow essence are smelted to XP on gather and never sit in the bag.
- Level is derived from XP on load; the stored level in the save file is cross-checked for consistency.
- Combat state is not saved. Mid-fight saves are not a feature.
- Death does not end the run. The player respawns at Spawn with a one-level penalty (see §11). The save is written immediately so the penalty is permanent even on quit.
- Dungeon difficulty ratios are applied at spawn time, not baked into the JSON enemy definition, so the same enemy can appear at different strengths in different dungeons.
- `validate_data` fails fast on startup for any broken reference — no silent defaults at runtime.

---

## 13. Browser UI

The browser version provides a responsive 1024×768 visual interface based on
the original Jeremy overworld artwork.

**Exploration:**
- All seven locations appear as paths on the overworld map
- **Move** opens the travel menu and animates Jeremy to the chosen location
- Locked locations remain visible with their required level
- Location-specific Gather, Fight, and Dungeon actions appear automatically

**Menus:**
- **Stats** — HP, effective PWR, XP, level, equipment, discoveries, and journeys
- **Bag** — interactive inventory with item quantities and descriptions
- **Gear** — current weapon/armor and equippable items from the bag
- **Craft** — recipes, owned/required materials, and affordability
- **Use item** — available consumables and their percentage-based healing
- Number keys 1–9 activate visible actions; Escape closes an open menu

**Combat:**
- Separate visual combat scene with player/enemy HP bars
- CLOSE/FAR distance indicator and weapon distance modifiers
- Attack, defend, use item, rush in/move back, and flee actions
- Status abilities, armor abilities, enemy speed, drops, XP, and level-ups
- Sequential dungeon floors followed by clear XP and item rewards

**Save/Load:**
- Actions save automatically to browser LocalStorage
- The Save action also writes the current state explicitly
- Browser saves are separate from the Python CLI save file

---

## 14. Ability Balancing & Scaling Caps (Late-Game)

To prevent high-level players from becoming invincible, six abilities are now capped based on item level:

| Ability | Scaling | Cap | Effect |
|---------|---------|-----|--------|
| **Lifesteal** | `heal = dmg × ratio` | `≤ missing_hp / 3` | Max 1/3 of missing HP healed per hit |
| **Berserker** | `max_bonus × item_level` | `≤ 5.0` (500%) | Max 500% damage at 0% HP |
| **Mark** | `1 + 0.2 × item_level` | `≤ 3.0` (×3 dmg) | Max 3× damage to marked enemies |
| **Regen** | `amount × item_level` | `≤ max_hp / 10` | Max 10% of effective max HP per round |
| **Poison** | `base + item_level - 1` | `≤ base × 8` | Max 8× base damage per tick |
| **Burn** | Infinite duration (old) | **5 ticks** (new) | Fixed 5-tick duration; magic weapons refresh to 5 ticks |

Caps apply to **both CLI and browser versions**. Non-scaled items are also capped where applicable (e.g., berserker club capped at 5× bonus).

The **Burn** ability now uses a tick system identical to **Poison**: `enemy["_burning"] = {dmg, ticks: 5}`. Each round decrements `ticks` and deletes the burn when ticks ≤ 0. Magic weapons re-apply burn (refreshing ticks to 5); melee/ranged weapons only apply if not already burning.

---

## 15. Inventory: Type Filtering & Discard

The inventory menu now features **type-based filtering** and a **discard option**:

**Filter menu:**
- "Show All" — all items in bag
- "Weapons" — slot == "weapon"
- "Armor" — slot == "armor"
- "Materials" — type == "material"
- "Consumables" — type == "consumable"
- "Back" — return to main menu

After selecting a filter, the player sees a list of items in that category. Clicking on an item displays **full details** (name, type, bonuses, abilities). Below the details, a submenu offers:
- "Back" — return to the filtered list
- "Discard 1" — remove 1 qty of the item from the bag

After discarding, the filtered list refreshes. Attempting to discard an equipped item fails silently (item not in bag).

---

## 16. The Labyrinth & The Timeless One

A new **end-game dungeon** accessible from Shadow Ruins at level 10+ introduces **permadeath** and a **6-phase revival boss**.

### Location & Mechanics

**The Labyrinth** (requires level 10):
- Located as a new world location with `min_level: 10`
- Entry warning: "You cannot flee. If you die here, your journey ends permanently."
- Players choose "Enter (no turning back)" or "Leave" — leaving returns to Shadow Ruins
- No flee option during labyrinth fights
- Death triggers `game_over` state: save file is deleted, player sees "Your journey has ended. The Labyrinth claimed your soul," and cannot continue that game

### 10 Floors: Left/Right Path Selection

Each of the 10 floors presents a **choice menu**: "Go Left (agile enemies)" or "Go Right (heavy enemies)"

**Left-path enemies** (agile, lower HP, higher PWR):
- Labyrinth Shade: hp 40, pwr 12, xp 50
- Labyrinth Wraith: hp 30, pwr 15, xp 55
- Labyrinth Hunter: hp 35, pwr 16, xp 55

**Right-path enemies** (heavy, higher HP, lower PWR):
- Labyrinth Golem: hp 60, pwr 10, xp 50
- Labyrinth Titan: hp 80, pwr 14, xp 60
- Labyrinth Beast: hp 50, pwr 18, xp 60

Enemies are **cycled by floor index** (`floor % 3`) so the same enemy appears multiple times. Dungeon scaling: `hp_ratio: 1.8, pwr_ratio: 1.3`.

### The Timeless One: 6-Phase Revival Boss

After clearing 10 floors, the player faces **The Timeless One** — a boss with **5 revivals** (6 total phases).

**Base stats** (scaled with `hp_ratio: 3.0, pwr_ratio: 2.0`):
- HP: 500 (scaled to ~1500 at player level 10)
- PWR: 50 (scaled to ~100 at player level 10)
- XP reward: 2000

**Revival mechanic:**
- When the boss reaches 0 HP:
  - If phase < 5: increment phase, print revival lore, scale stats, clear DOT effects, restore HP, continue fight
  - Else (phase = 5): declare victory, end combat
- Revival scaling: `new_hp = original_hp × (1 + phase × 0.4)`, `new_pwr = original_pwr × (1 + phase × 0.25)`
- After phase 1: boss hp × 1.4, pwr × 1.25
- After phase 5: boss hp × 3.0, pwr × 2.25

**Lore & Revival Messages:**
1. "I have died a thousand times and returned a thousand more."
2. "Every wound you deal me, I have already healed in another era."
3. "I remember the fall of your ancestors. They also thought themselves worthy."
4. "I will end this age as I ended all ages before it."
5. "THIS IS MY FINAL FORM. DIE AS ALL THINGS DIE. BY MY HAND."

Each revival clears poison, burn, mark, and chill effects from the boss to prevent pre-applied DOTs from killing it between phases.

### End-game Flag

Defeating The Timeless One triggers a victory message. **No post-game content exists yet** — this is the current end milestone. Future updates may add an epilogue or new-game+ mode.

---

## 18. Mana System & Spell Abilities

Magic weapons and some armor pieces now introduce a **mana system** for casting spells and special abilities.

**Mana Mechanics:**
- **Max Mana**: 100 (base, not affected by leveling)
- **Mana Regen**: 5 per round (regenerated at the start of each combat round)
- **Mana Pool Boost**: Certain items (e.g., Spectral Circlet) increase max mana
- **Mana Regen Boost**: Certain items (e.g., Mystic Robe) add to the base 5 regen per round

**Spell Abilities (mana-based):**
Spells consume mana when cast and have the following types:

| Spell | Mana Cost | Effect |
|-------|-----------|--------|
| **Spell Freeze** | 12 | Chills enemy for 4 PWR reduction, +30% damage |
| **Spell Fireball** | 15 | Deals 1.5× scaled damage |
| **Spell Heal** | 20 | Restores 40% of max HP to player |
| **Spell Shock** | 18 | Deals 2× scaled damage (lightning) |
| **Arcane Surge** | 10 | Deals 1.8× scaled damage, uses arcane power |
| **Spell Void** | 25 | Deals 2.5× scaled damage (highest cost, highest reward) |
| **Spell Drain** | 16 | Deals damage and lifesteals 40% of damage |
| **Stone Skin** | 8 | Grants shield equal to 50% of incoming damage |
| **Frost Shield** | 10 | Grants 5-point shield against damage |
| **Spell Crystal** | 14 | Deals 1.4× damage, reflects 10% back to attacker |

**Non-mana Spell Abilities (instant, no cost):**
- **Fortify Aura**: Reduces incoming damage by 3 (costs 12 mana but passive)
- **Mana Regen Boost**: Adds to mana regen per round
- **Mana Pool Boost**: Increases max mana capacity

Spells are only available when the player has equipped a magic weapon or armor with a spell ability. If mana is insufficient, the spell cannot be cast and the player must choose a different action.

---

## 19. New Craftable Items (30 Total)

Added **30 new level-scaled craftable items** with varied crafting requirements and strategic abilities:

**Mana-Using Magic Weapons (7):**
- Frostbolt Staff (crystal 3, iron 2)
- Fireball Tome (ember 3, crystal 2)
- Heal Grimoire (herb 4, crystal 2)
- Lightning Rod (crystal 4, iron 3)
- Void Staff (shadow_essence 2, crystal 4)
- Obsidian Staff (stone 4, shadow_essence 1)
- Crystal Wand (crystal 4, iron 1)

**Melee Weapons (8):**
- Arcane Blade (iron 3, crystal 2)
- Dexterous Claws (iron 2, hide 1)
- Shadow Step Dagger (iron 2, shadow_essence 1)
- Vortex Axe (iron 4, stone 2)
- Consecrated Hammer (iron 4, herb 2)
- Flame Tongue Sword (iron 3, ember 2)
- Tide Caller Trident (iron 4, crystal 2)
- [existing: Berserker Club, Mark Blade, Poison Dagger]

**Ranged Weapons (5):**
- Spiraling Pike (iron 3, stone 1)
- Glacial Lance (crystal 3, iron 2)
- Phantom Bow (wood 3, hide 2)
- Fey Bow (wood 3, crystal 1)
- [existing: Swift Longbow]

**Armor Pieces (10):**
- Stoneward Armor (stone 5, iron 3) — stone_skin ability
- Thorned Gauntlets (iron 3, stone 2) — thorns 4
- Ice Armor (crystal 3, stone 2) — frost_shield
- Inferno Cloak (ember 3, hide 2) — burn
- Mystic Robe (crystal 3, herb 2) — mana_regen_boost
- Warden Shield (stone 5, iron 2) — shield 4
- Runed Boots (hide 2, crystal 1) — regen 2
- Spectral Circlet (crystal 3, shadow_essence 1) — mana_pool_boost 20
- Spiked Sabatons (iron 3, stone 1) — thorns 3
- Twilight Robe (hide 3, crystal 1) — regen 3
- Blessed Plate (stone 5, crystal 1) — shield 5
- Dragonscale Mail (stone 6, crystal 2) — shield 6
- [existing: Shield Plate, Leather Armor, Drake Armor]

All 30 items are **level-scaled** (bonus scales with item level) and are available to craft once materials are gathered.

---

## 20. Parked / future ideas

- Additional biome tiers beyond Shadow Ruins (ice tundra, void realm, …).
- Hunger / stamina layer affecting gather yield or combat performance.
- Multi-enemy encounters and enemy formations.
- Ranged enemy attacks that bypass guard.
- More consumable kinds: stamina leaf (boost gather), smoke bomb (guaranteed flee).
- Player speed stat and multi-attack moves for the player.
- Boss enemies at the end of each dungeon (currently dungeons end on a regular enemy).
- Difficulty settings that adjust XP thresholds or enemy scaling ratios.
- **Web version enhancements:** additional map art, enemy sprites, richer sound effects, and networked multiplayer
