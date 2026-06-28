import test from "node:test";
import assert from "node:assert/strict";

import { GameEngine } from "./core.js";

function fixture() {
  return {
    world: {
      spawn: { name: "Spawn", description: "Safe", enemies: [], gather: [] },
      forest: {
        name: "Forest",
        description: "Trees",
        enemies: [],
        gather: [
          { kind: "item", id: "wood", min: 1, max: 3 },
          { kind: "xp", min: 1, max: 2 },
        ],
      },
      volcano: { name: "Volcano", description: "Hot", min_level: 3, enemies: [], gather: [] },
      jungle: { name: "Jungle", description: "Wild", enemies: ["snake"], gather: [] },
    },
    items: {
      wood: { name: "Wood", type: "material" },
      herb: { name: "Herb", type: "material" },
      potion: { name: "Potion", type: "consumable", effect: { kind: "heal", ratio: 0.5 } },
      spear: { name: "Spear", type: "craftable", equip: { slot: "weapon", weapon_type: "ranged", level_scaled: true } },
    },
    enemies: {
      snake: { name: "Snake", type: "ranged", hp: 5, pwr: 3, speed: 2, xp: 5, drops: [] },
    },
    recipes: {
      spear: { name: "Spear", requires: { wood: 1 }, creates: { spear: 1 } },
    },
    dungeons: {},
  };
}

test("travel respects level locks", () => {
  const game = new GameEngine(fixture());
  assert.equal(game.travel("forest").ok, true);
  assert.equal(game.travel("volcano").ok, false);
  assert.equal(game.state.location, "forest");
});

test("gathering adds resources and XP", () => {
  const game = new GameEngine(fixture(), { ...GameEngine.newState(), location: "forest" }, () => 0);
  const result = game.gather();
  assert.equal(result.ok, true);
  assert.equal(game.state.bag.wood, 1);
  assert.equal(game.state.xp, 1);
});

test("crafting rolls a level and equipment affects power", () => {
  const game = new GameEngine(fixture(), { ...GameEngine.newState(), bag: { wood: 1 } }, () => 0);
  assert.equal(game.craft("spear").ok, true);
  assert.equal(game.equip("spear").ok, true);
  assert.equal(game.effectivePwr(), 4);
});

test("consumables heal without being wasted at full health", () => {
  const game = new GameEngine(fixture(), { ...GameEngine.newState(), hp: 8, bag: { potion: 2 } });
  assert.equal(game.useItem("potion").ok, true);
  assert.equal(game.state.hp, 18);
  assert.equal(game.state.bag.potion, 1);
  game.state.hp = game.effectiveMaxHp();
  assert.equal(game.useItem("potion").ok, false);
  assert.equal(game.state.bag.potion, 1);
});

test("speed-two enemy attacks twice and guard affects only the first hit", () => {
  const game = new GameEngine(fixture(), { ...GameEngine.newState(), location: "jungle" }, () => 0.99);
  game.startFight("snake");
  const result = game.defend();
  assert.equal(result.status, "continue");
  assert.equal(game.state.hp, 15); // ceil(3/2) + 3
});
