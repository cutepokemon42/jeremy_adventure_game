export const SAVE_KEY = "jeremy-visual-save-v1";

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const roll = (min, max, rng = Math.random) => min + Math.floor(rng() * (max - min + 1));

export class GameEngine {
  constructor(content, savedState = null, rng = Math.random) {
    this.content = content;
    this.rng = rng;
    this.state = savedState ?? GameEngine.newState();
    this.combat = null;
    this.normalizeState();
  }

  static newState() {
    return {
      hp: 20,
      maxHp: 20,
      pwr: 3,
      xp: 0,
      level: 1,
      location: "spawn",
      bag: {},
      weapon: null,
      armor: null,
      itemLevels: {},
      discovered: ["spawn"],
      steps: 0,
    };
  }

  normalizeState() {
    const base = GameEngine.newState();
    this.state = { ...base, ...this.state };
    this.state.bag = { ...this.state.bag };
    this.state.itemLevels = { ...this.state.itemLevels };
    this.state.discovered = [...new Set(this.state.discovered ?? ["spawn"])];
    if (!this.content.world[this.state.location]) this.state.location = "spawn";
    this.state.level = this.levelForXp(this.state.xp);
    this.state.maxHp = 20 + (this.state.level - 1) * 5;
    this.state.pwr = 3 + (this.state.level - 1);
    this.state.hp = clamp(Number(this.state.hp) || 0, 0, this.effectiveMaxHp());
  }

  levelForXp(xp) {
    return Math.max(1, Math.floor(Math.max(0, xp) / 10) + 1);
  }

  effectivePwr() {
    const item = this.content.items[this.state.weapon];
    if (!item?.equip) return this.state.pwr;
    const bonus = item.equip.level_scaled
      ? (this.state.itemLevels[this.state.weapon] ?? 1)
      : (item.equip.pwr_bonus ?? 0);
    return this.state.pwr + bonus;
  }

  effectiveMaxHp() {
    const item = this.content.items[this.state.armor];
    if (!item?.equip) return this.state.maxHp;
    const bonus = item.equip.level_scaled
      ? (this.state.itemLevels[this.state.armor] ?? 1) * 4
      : (item.equip.max_hp_bonus ?? 0);
    return this.state.maxHp + bonus;
  }

  gainXp(amount) {
    const previousLevel = this.state.level;
    this.state.xp += Math.max(0, amount);
    const nextLevel = this.levelForXp(this.state.xp);
    if (nextLevel > previousLevel) {
      this.state.level = nextLevel;
      this.state.maxHp = 20 + (nextLevel - 1) * 5;
      this.state.pwr = 3 + (nextLevel - 1);
      this.state.hp = this.effectiveMaxHp();
    }
    return nextLevel - previousLevel;
  }

  addItem(itemId, quantity = 1) {
    if (quantity <= 0) return;
    this.state.bag[itemId] = (this.state.bag[itemId] ?? 0) + quantity;
  }

  removeItems(costs) {
    if (!this.hasItems(costs)) return false;
    Object.entries(costs).forEach(([itemId, quantity]) => {
      this.state.bag[itemId] -= quantity;
      if (this.state.bag[itemId] <= 0) delete this.state.bag[itemId];
    });
    return true;
  }

  hasItems(costs) {
    return Object.entries(costs).every(([itemId, quantity]) => (this.state.bag[itemId] ?? 0) >= quantity);
  }

  rollItemLevel(itemId) {
    if (!this.content.items[itemId]?.equip?.level_scaled) return null;
    const level = roll(Math.max(1, this.state.pwr - 2), this.state.pwr, this.rng);
    this.state.itemLevels[itemId] = Math.max(this.state.itemLevels[itemId] ?? 0, level);
    return level;
  }

  location() {
    return this.content.world[this.state.location];
  }

  availableLocations() {
    return Object.entries(this.content.world).map(([id, location]) => ({
      id,
      ...location,
      locked: this.state.level < (location.min_level ?? 1),
      current: id === this.state.location,
    }));
  }

  travel(locationId) {
    const location = this.content.world[locationId];
    if (!location) return { ok: false, message: "That route does not exist." };
    const required = location.min_level ?? 1;
    if (this.state.level < required) {
      return { ok: false, message: `${location.name} unlocks at level ${required}.` };
    }
    if (locationId === this.state.location) return { ok: false, message: `You are already at ${location.name}.` };
    this.state.location = locationId;
    this.state.steps += 1;
    if (!this.state.discovered.includes(locationId)) this.state.discovered.push(locationId);
    return { ok: true, message: `You follow the path to ${location.name}. ${location.description}` };
  }

  gather() {
    const location = this.location();
    if (!location.gather?.length) return { ok: false, message: "There is nothing useful to gather here." };
    const found = [];
    let xp = 0;
    location.gather.forEach((entry) => {
      const quantity = roll(entry.min, entry.max, this.rng);
      if (quantity <= 0) return;
      if (entry.kind === "xp") {
        xp += quantity;
        return;
      }
      const item = this.content.items[entry.id];
      if (item?.xp_value) {
        const gained = item.xp_value * quantity;
        xp += gained;
        found.push(`${quantity} ${item.name} smelted into ${gained} XP`);
      } else {
        this.addItem(entry.id, quantity);
        found.push(`${quantity} ${item?.name ?? entry.id}`);
      }
    });
    const levels = xp ? this.gainXp(xp) : 0;
    if (xp && !found.some((part) => part.includes("XP"))) found.push(`${xp} XP`);
    if (!found.length) return { ok: true, message: "You search carefully but find nothing this time." };
    return {
      ok: true,
      message: `You gathered ${found.join(", ")}.${levels ? ` Level up! You are now level ${this.state.level}.` : ""}`,
    };
  }

  craft(recipeId) {
    const recipe = this.content.recipes[recipeId];
    if (!recipe) return { ok: false, message: "You do not know that recipe." };
    if (!this.removeItems(recipe.requires)) return { ok: false, message: `You are missing materials for ${recipe.name}.` };
    const created = [];
    Object.entries(recipe.creates).forEach(([itemId, quantity]) => {
      this.addItem(itemId, quantity);
      const level = this.rollItemLevel(itemId);
      created.push(`${this.content.items[itemId]?.name ?? itemId}${level ? ` (level ${level})` : ""}`);
    });
    return { ok: true, message: `Crafted ${created.join(", ")}.` };
  }

  equip(itemId) {
    const item = this.content.items[itemId];
    const slot = item?.equip?.slot;
    if (!slot || !["weapon", "armor"].includes(slot)) return { ok: false, message: "That item cannot be equipped." };
    if ((this.state.bag[itemId] ?? 0) < 1) return { ok: false, message: "That item is not in your bag." };
    const previous = this.state[slot];
    this.removeItems({ [itemId]: 1 });
    if (previous) this.addItem(previous, 1);
    this.state[slot] = itemId;
    this.state.hp = Math.min(this.state.hp, this.effectiveMaxHp());
    return { ok: true, message: `Equipped ${item.name}${previous ? ` and stowed ${this.content.items[previous]?.name ?? previous}` : ""}.` };
  }

  useItem(itemId) {
    const item = this.content.items[itemId];
    if (item?.type !== "consumable" || (this.state.bag[itemId] ?? 0) < 1) {
      return { ok: false, message: "That item cannot be used." };
    }
    const cap = this.effectiveMaxHp();
    if (this.state.hp >= cap) return { ok: false, message: "You are already at full health." };
    const effect = item.effect ?? {};
    const amount = effect.amount ?? Math.max(1, Math.round(cap * (effect.ratio ?? 0)));
    const healed = Math.min(amount, cap - this.state.hp);
    this.state.hp += healed;
    this.removeItems({ [itemId]: 1 });
    return { ok: true, message: `${item.name} restores ${healed} HP.` };
  }

  weaponType() {
    return this.content.items[this.state.weapon]?.equip?.weapon_type ?? "melee";
  }

  slotAbility(slot) {
    const itemId = this.state[slot];
    return this.content.items[itemId]?.equip?.ability ?? {};
  }

  startFight(enemyId = null, options = {}) {
    const choices = this.location().enemies ?? [];
    enemyId ??= choices[Math.floor(this.rng() * choices.length)];
    const definition = this.content.enemies[enemyId];
    if (!definition) return { ok: false, message: "There are no enemies here." };
    let hp = definition.hp;
    let pwr = definition.pwr;
    if (options.difficulty) {
      hp = Math.max(hp, Math.floor(this.effectiveMaxHp() * (options.difficulty.hp_ratio ?? 1)));
      pwr = Math.max(pwr, Math.floor(this.effectivePwr() * (options.difficulty.pwr_ratio ?? 1)));
    } else {
      const scale = 1 + Math.max(0, this.state.level - 2) * 0.15;
      hp = Math.max(hp, Math.round(hp * scale));
      pwr = Math.max(pwr, Math.round(pwr * scale));
    }
    this.combat = {
      id: enemyId,
      name: definition.name,
      type: definition.type ?? "melee",
      hp,
      maxHp: hp,
      pwr,
      speed: definition.speed ?? 1,
      xp: definition.xp,
      drops: definition.drops ?? [],
      distance: definition.type === "ranged" ? "far" : "close",
      burning: 0,
      poison: null,
      marked: false,
      chilled: 0,
      dungeon: options.dungeon ?? null,
    };
    this.startRound();
    return { ok: true, message: `A ${definition.name} appears at ${this.combat.distance.toUpperCase()} range!` };
  }

  startRound() {
    if (!this.combat) return null;
    const notes = [];
    if (this.combat.burning) {
      this.combat.hp -= this.combat.burning;
      notes.push(`${this.combat.name} burns for ${this.combat.burning}.`);
    }
    if (this.combat.poison) {
      this.combat.hp -= this.combat.poison.damage;
      this.combat.poison.ticks -= 1;
      notes.push(`Poison deals ${this.combat.poison.damage}.`);
      if (this.combat.poison.ticks <= 0) this.combat.poison = null;
    }
    const armorAbility = this.slotAbility("armor");
    if (armorAbility.kind === "regen") {
      const healed = Math.min(armorAbility.amount, this.effectiveMaxHp() - this.state.hp);
      this.state.hp += healed;
      if (healed) notes.push(`Your armor restores ${healed} HP.`);
    }
    return notes;
  }

  playerAttack() {
    if (!this.combat) return { ok: false, message: "There is no active fight." };
    const enemy = this.combat;
    const type = this.weaponType();
    const ability = this.slotAbility("weapon");
    let multiplier = 1;
    if (type === "melee" && enemy.distance === "far") multiplier = 0.6;
    if (type === "ranged" && enemy.distance === "close") multiplier = 0.8;
    if (ability.kind === "swift") multiplier = 1;
    if (enemy.marked) multiplier *= ability.bonus_mult ?? 1.2;
    if (ability.kind === "berserker") {
      const missing = 1 - this.state.hp / this.effectiveMaxHp();
      multiplier *= 1 + missing * ability.max_bonus;
    }
    if (ability.kind === "execute" && enemy.hp < enemy.maxHp * ability.threshold) multiplier *= ability.bonus;
    const damage = Math.max(1, Math.round(this.effectivePwr() * multiplier));
    enemy.hp -= damage;
    const notes = [`You strike ${enemy.name} for ${damage}.`];
    if (ability.kind === "lifesteal") {
      const healed = Math.min(Math.max(1, Math.floor(damage * ability.ratio)), this.effectiveMaxHp() - this.state.hp);
      this.state.hp += healed;
      if (healed) notes.push(`Lifesteal restores ${healed} HP.`);
    }
    if (enemy.hp > 0) {
      if (ability.kind === "chill") enemy.chilled = ability.amount;
      if (ability.kind === "burn" && (!enemy.burning || type === "magic")) enemy.burning = ability.damage;
      if (ability.kind === "poison" && (!enemy.poison || type === "magic")) enemy.poison = { damage: ability.damage, ticks: ability.ticks };
      if (ability.kind === "mark") enemy.marked = true;
    }
    if (enemy.hp <= 0) return this.victory(notes);
    return this.enemyTurn(false, notes);
  }

  defend() {
    if (!this.combat) return { ok: false, message: "There is no active fight." };
    return this.enemyTurn(true, ["You brace for the next strike."]);
  }

  changeDistance() {
    if (!this.combat) return { ok: false, message: "There is no active fight." };
    this.combat.distance = this.combat.distance === "close" ? "far" : "close";
    const note = this.combat.distance === "close" ? "You rush into close range." : "You move back to far range.";
    return this.enemyTurn(false, [note]);
  }

  enemyTurn(guarded, notes = []) {
    const enemy = this.combat;
    if (!enemy) return { ok: false, message: "There is no active fight." };
    const type = this.weaponType();
    let multiplier = 1;
    if (type === "ranged" && enemy.distance === "far") multiplier = 0.75;
    else if (enemy.type === "ranged" && enemy.distance === "close") multiplier = 0.7;
    let pwr = Math.max(1, Math.floor(enemy.pwr * multiplier) - enemy.chilled);
    enemy.chilled = 0;
    const armor = this.slotAbility("armor");
    for (let hit = 0; hit < enemy.speed; hit += 1) {
      let damage = guarded && hit === 0 ? Math.max(1, Math.ceil(pwr / 2)) : pwr;
      if (armor.kind === "shield") damage = Math.max(1, damage - armor.amount);
      if (armor.kind === "fortify" && this.state.hp < this.effectiveMaxHp() * 0.3) damage = Math.max(1, Math.ceil(damage / 2));
      this.state.hp -= damage;
      notes.push(`${enemy.name} ${hit ? "strikes again" : "hits you"} for ${damage}.`);
      if (armor.kind === "thorns") {
        enemy.hp -= armor.amount;
        notes.push(`Thorns reflect ${armor.amount}.`);
        if (enemy.hp <= 0) return this.victory(notes);
      }
      if (this.state.hp <= 0) return this.defeat(notes);
    }
    const roundNotes = this.startRound() ?? [];
    notes.push(...roundNotes);
    if (enemy.hp <= 0) return this.victory(notes);
    return { ok: true, status: "continue", message: notes.join(" ") };
  }

  victory(notes = []) {
    const enemy = this.combat;
    const levelGain = this.gainXp(enemy.xp);
    const loot = [];
    enemy.drops.forEach((drop) => {
      if (this.rng() <= drop.chance) {
        const quantity = roll(drop.min, drop.max, this.rng);
        this.addItem(drop.id, quantity);
        const itemLevel = this.rollItemLevel(drop.id);
        loot.push(`${quantity} ${this.content.items[drop.id]?.name ?? drop.id}${itemLevel ? ` (level ${itemLevel})` : ""}`);
      }
    });
    notes.push(`Victory! You gain ${enemy.xp} XP.`);
    if (loot.length) notes.push(`Loot: ${loot.join(", ")}.`);
    if (levelGain) notes.push(`Level up! You are now level ${this.state.level}.`);
    const dungeon = enemy.dungeon;
    this.combat = null;
    return { ok: true, status: "victory", message: notes.join(" "), dungeon };
  }

  defeat(notes = []) {
    const oldLevel = this.state.level;
    const newLevel = Math.max(1, oldLevel - 1);
    this.state.xp = (newLevel - 1) * 10;
    this.state.level = newLevel;
    this.state.maxHp = 20 + (newLevel - 1) * 5;
    this.state.pwr = 3 + (newLevel - 1);
    this.state.location = "spawn";
    this.state.hp = this.effectiveMaxHp();
    this.combat = null;
    notes.push(`You fall in battle and wake at Spawn${oldLevel > newLevel ? ` at level ${newLevel}` : ""}.`);
    return { ok: true, status: "defeat", message: notes.join(" ") };
  }

  flee() {
    if (!this.combat) return { ok: false, message: "There is no fight to flee." };
    this.combat = null;
    return { ok: true, status: "flee", message: "You escape along the path." };
  }

  serialize() {
    return JSON.stringify(this.state);
  }
}

export function loadSavedState(storage = globalThis.localStorage) {
  try {
    const raw = storage?.getItem(SAVE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveState(state, storage = globalThis.localStorage) {
  storage?.setItem(SAVE_KEY, JSON.stringify(state));
}
