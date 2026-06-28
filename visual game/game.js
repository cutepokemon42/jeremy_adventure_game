import { GameEngine, loadSavedState, saveState } from "./core.js";

const $ = (selector) => document.querySelector(selector);
const elements = {
  locationName: $("#location-name"),
  locationCardName: $("#location-card-name"),
  locationKicker: $("#location-kicker"),
  hp: $("#hp-stat"),
  pwr: $("#pwr-stat"),
  level: $("#level-stat"),
  xp: $("#xp-stat"),
  message: $("#message"),
  actions: $("#action-list"),
  marker: $("#player-marker"),
  mapNodes: $("#map-nodes"),
  modal: $("#modal"),
  modalKicker: $("#modal-kicker"),
  modalTitle: $("#modal-title"),
  modalContent: $("#modal-content"),
  combat: $("#combat"),
  enemyName: $("#enemy-name"),
  enemySprite: $("#enemy-sprite"),
  enemyHp: $("#enemy-hp"),
  enemyBar: $("#enemy-health-bar"),
  heroHp: $("#hero-hp"),
  heroBar: $("#hero-health-bar"),
  combatDistance: $("#combat-distance"),
  combatMessage: $("#combat-message"),
  combatActions: $("#combat-actions"),
};

const MAP_POSITIONS = {
  spawn: [64, 76],
  forest: [27, 72],
  jungle: [78, 64],
  mines: [82, 25],
  deep_mine: [93, 16],
  volcano: [58, 18],
  shadow_ruins: [23, 28],
};

const LOCATION_TAGS = {
  spawn: "Safe camp",
  forest: "Quiet trail",
  jungle: "Wild territory",
  mines: "Ore tunnels",
  deep_mine: "Lower caverns",
  volcano: "Scorched summit",
  shadow_ruins: "Ancient darkness",
};

const ACTION_ICONS = {
  travel: "➜",
  gather: "♧",
  fight: "⚔",
  dungeon: "▣",
  inventory: "▤",
  craft: "◆",
  equip: "◈",
  use: "+",
  stats: "▥",
  save: "✓",
};

const ENEMY_SPRITES = {
  boar: "🐗",
  snake: "🐍",
  cave_bat: "🦇",
  rock_golem: "🗿",
  lava_lizard: "🦎",
  fire_drake: "🐉",
  shade_walker: "👤",
  bone_knight: "💀",
  shadow_archer: "🏹",
};

let engine;
let content;
let soundEnabled = true;

async function loadJson(path, rootKey) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return (await response.json())[rootKey];
}

async function boot() {
  try {
    const [world, items, enemies, recipes, dungeons] = await Promise.all([
      loadJson("../data/world.json", "locations"),
      loadJson("../data/items.json", "items"),
      loadJson("../data/enemies.json", "enemies"),
      loadJson("../data/recipes.json", "recipes"),
      loadJson("../data/dungeons.json", "dungeons"),
    ]);
    content = { world, items, enemies, recipes, dungeons };
    engine = new GameEngine(content, loadSavedState());
    bindGlobalControls();
    render();
    setMessage("The crossroads are alive. Choose a path or prepare at camp.");
  } catch (error) {
    elements.message.textContent = `${error.message}. Start the game through the included local server.`;
    elements.actions.innerHTML = "<p class='empty-state'>Game data could not be loaded.</p>";
  }
}

function bindGlobalControls() {
  document.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeModal));
  $("#combat-flee-top").addEventListener("click", () => handleCombatResult(engine.flee()));
  $("#sound-toggle").addEventListener("click", (event) => {
    soundEnabled = !soundEnabled;
    event.currentTarget.textContent = soundEnabled ? "♪" : "×";
    event.currentTarget.title = soundEnabled ? "Sound on" : "Sound off";
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!elements.modal.hidden) closeModal();
      return;
    }
    if (!elements.modal.hidden || !elements.combat.hidden) return;
    const number = Number(event.key);
    if (number >= 1) elements.actions.querySelector(`button:nth-child(${number})`)?.click();
  });
}

function actionsForLocation() {
  const location = engine.location();
  const actions = [
    { id: "travel", label: "Move", hint: "Choose a path", run: showTravel },
  ];
  if (location.gather?.length) actions.push({ id: "gather", label: "Gather", hint: "Search this area", run: gather });
  if (location.enemies?.length) actions.push({ id: "fight", label: "Fight", hint: "Hunt a wild enemy", run: fight });
  if (location.dungeon) actions.push({ id: "dungeon", label: "Dungeon", hint: content.dungeons[location.dungeon]?.name ?? "Enter", run: enterDungeon });
  actions.push(
    { id: "inventory", label: "Bag", hint: "View your items", run: showInventory },
    { id: "craft", label: "Craft", hint: "Build useful gear", run: showCrafting },
    { id: "equip", label: "Gear", hint: "Equip weapons & armor", run: showEquipment },
    { id: "use", label: "Use item", hint: "Restore health", run: showConsumables },
    { id: "stats", label: "Stats", hint: "Review your build", run: showStats },
    { id: "save", label: "Save", hint: "Store this adventure", run: manualSave },
  );
  return actions.slice(0, 9);
}

function render() {
  const state = engine.state;
  const location = engine.location();
  const maxHp = engine.effectiveMaxHp();
  elements.locationName.textContent = location.name;
  elements.locationCardName.textContent = location.name.toUpperCase();
  elements.locationKicker.textContent = LOCATION_TAGS[state.location] ?? "Unknown road";
  elements.hp.textContent = `${state.hp} / ${maxHp}`;
  elements.pwr.textContent = engine.effectivePwr();
  elements.level.textContent = state.level;
  elements.xp.textContent = `${state.xp % 10} / 10`;
  const [left, top] = MAP_POSITIONS[state.location] ?? MAP_POSITIONS.spawn;
  elements.marker.style.left = `${left}%`;
  elements.marker.style.top = `${top}%`;
  renderMapNodes();
  renderActions();
}

function renderMapNodes() {
  elements.mapNodes.replaceChildren();
  engine.availableLocations().forEach((location) => {
    const [left, top] = MAP_POSITIONS[location.id] ?? [50, 50];
    const node = document.createElement("span");
    node.className = `map-node${location.locked ? " locked" : ""}${location.current ? " current" : ""}`;
    node.style.left = `${left}%`;
    node.style.top = `${top}%`;
    elements.mapNodes.append(node);
  });
}

function renderActions() {
  elements.actions.replaceChildren();
  actionsForLocation().forEach((action, index) => {
    const button = document.createElement("button");
    button.className = "action-button";
    button.innerHTML = `
      <span class="action-number">${index + 1}</span>
      <span class="action-copy"><strong>${action.label}</strong><small>${action.hint}</small></span>
      <span class="action-glyph" aria-hidden="true">${ACTION_ICONS[action.id]}</span>`;
    button.addEventListener("click", action.run);
    elements.actions.append(button);
  });
}

function setMessage(message) {
  elements.message.textContent = message;
}

function commitResult(result, { close = false } = {}) {
  setMessage(result.message);
  if (result.ok) {
    saveState(engine.state);
    playTone(420, 0.045);
  } else {
    playTone(150, 0.07);
  }
  if (close) closeModal();
  render();
  return result;
}

function gather() {
  commitResult(engine.gather());
}

function fight() {
  const result = engine.startFight();
  if (!result.ok) return commitResult(result);
  openCombat(result.message);
}

function enterDungeon() {
  const dungeonId = engine.location().dungeon;
  const dungeon = content.dungeons[dungeonId];
  if (!dungeon) return;
  if (engine.state.level < (dungeon.min_level ?? 1)) {
    return commitResult({ ok: false, message: `${dungeon.name} requires level ${dungeon.min_level}.` });
  }
  openModal(dungeon.name, "Dungeon", (container) => {
    const summary = document.createElement("div");
    summary.className = "detail-grid";
    summary.innerHTML = `
      <div class="detail-card"><small>Floors</small><strong>${dungeon.floors.length}</strong></div>
      <div class="detail-card"><small>Clear bonus</small><strong>${dungeon.bonus_xp} XP</strong></div>`;
    container.append(summary);
    container.append(makeRow({
      icon: "⚔",
      title: "Enter dungeon",
      detail: dungeon.description,
      meta: "Begin",
      onClick: () => {
        closeModal();
        const result = engine.startFight(dungeon.floors[0], {
          difficulty: dungeon.difficulty,
          dungeon: { id: dungeonId, floor: 0 },
        });
        openCombat(result.message);
      },
    }));
  });
}

function showTravel() {
  openModal("Choose a path", "Travel", (container) => {
    const grid = menuGrid(container);
    engine.availableLocations().forEach((location) => {
      grid.append(makeRow({
        icon: location.locked ? "⌁" : location.current ? "●" : "➜",
        title: location.name,
        detail: location.locked ? `Unlocks at level ${location.min_level}` : location.description,
        meta: location.current ? "Here" : location.locked ? "Locked" : "Travel",
        disabled: location.locked || location.current,
        onClick: () => commitResult(engine.travel(location.id), { close: true }),
      }));
    });
  });
}

function showInventory() {
  openModal("Your bag", "Inventory", (container) => {
    const entries = Object.entries(engine.state.bag).filter(([, quantity]) => quantity > 0);
    if (!entries.length) return empty(container, "Your bag is empty. Gather resources or win battles to find items.");
    const grid = menuGrid(container);
    entries.forEach(([itemId, quantity]) => {
      const item = content.items[itemId] ?? { name: itemId, type: "unknown" };
      const level = engine.state.itemLevels[itemId];
      grid.append(makeRow({
        icon: itemIcon(item),
        title: `${item.name}${level ? ` · Lv ${level}` : ""}`,
        detail: describeItem(itemId),
        meta: `×${quantity}`,
      }));
    });
  });
}

function showCrafting() {
  openModal("Build equipment", "Crafting", (container) => {
    const grid = menuGrid(container);
    Object.entries(content.recipes).forEach(([recipeId, recipe]) => {
      const affordable = engine.hasItems(recipe.requires);
      const costs = Object.entries(recipe.requires)
        .map(([id, quantity]) => `${content.items[id]?.name ?? id} ${engine.state.bag[id] ?? 0}/${quantity}`)
        .join(" · ");
      grid.append(makeRow({
        icon: "◆",
        title: recipe.name,
        detail: costs,
        meta: affordable ? "Craft" : "Missing",
        disabled: !affordable,
        onClick: () => {
          commitResult(engine.craft(recipeId));
          showCrafting();
        },
      }));
    });
  });
}

function showEquipment() {
  openModal("Choose your build", "Equipment", (container) => {
    const equipped = document.createElement("div");
    equipped.className = "detail-grid";
    equipped.innerHTML = `
      <div class="detail-card"><small>Weapon</small><strong>${content.items[engine.state.weapon]?.name ?? "Unarmed"}</strong></div>
      <div class="detail-card"><small>Armor</small><strong>${content.items[engine.state.armor]?.name ?? "None"}</strong></div>`;
    container.append(equipped);
    const ids = Object.keys(engine.state.bag).filter((id) => content.items[id]?.equip && engine.state.bag[id] > 0);
    if (!ids.length) return empty(container, "Craft or find equipment, then return here to equip it.");
    const grid = menuGrid(container);
    ids.forEach((itemId) => {
      const item = content.items[itemId];
      grid.append(makeRow({
        icon: item.equip.slot === "weapon" ? "⚔" : "◈",
        title: item.name,
        detail: describeItem(itemId),
        meta: "Equip",
        onClick: () => {
          commitResult(engine.equip(itemId));
          showEquipment();
        },
      }));
    });
  });
}

function showConsumables() {
  openModal("Restore health", "Use item", (container) => {
    const ids = consumableIds();
    if (!ids.length) return empty(container, "You have no usable consumables.");
    const grid = menuGrid(container);
    ids.forEach((itemId) => {
      const item = content.items[itemId];
      grid.append(makeRow({
        icon: "+",
        title: item.name,
        detail: `${describeItem(itemId)} · ${engine.state.bag[itemId]} available`,
        meta: "Use",
        onClick: () => {
          commitResult(engine.useItem(itemId));
          showConsumables();
        },
      }));
    });
  });
}

function showStats() {
  openModal("Jeremy's build", "Stats", (container) => {
    const cards = [
      ["Health", `${engine.state.hp} / ${engine.effectiveMaxHp()}`],
      ["Power", engine.effectivePwr()],
      ["Level", engine.state.level],
      ["Total XP", engine.state.xp],
      ["Weapon", content.items[engine.state.weapon]?.name ?? "Unarmed"],
      ["Armor", content.items[engine.state.armor]?.name ?? "None"],
      ["Places found", `${engine.state.discovered.length} / ${Object.keys(content.world).length}`],
      ["Journeys", engine.state.steps],
    ];
    const grid = document.createElement("div");
    grid.className = "detail-grid";
    cards.forEach(([label, value]) => {
      const card = document.createElement("div");
      card.className = "detail-card";
      card.innerHTML = `<small>${label}</small><strong>${value}</strong>`;
      grid.append(card);
    });
    container.append(grid);
  });
}

function manualSave() {
  saveState(engine.state);
  setMessage("Adventure saved in this browser.");
  playTone(620, 0.08);
}

function openModal(title, kicker, renderContent) {
  elements.modalTitle.textContent = title;
  elements.modalKicker.textContent = kicker;
  elements.modalContent.replaceChildren();
  renderContent(elements.modalContent);
  elements.modal.hidden = false;
  elements.modal.querySelector("button")?.focus();
}

function closeModal() {
  elements.modal.hidden = true;
  elements.modalContent.replaceChildren();
}

function menuGrid(container) {
  const grid = document.createElement("div");
  grid.className = "menu-grid";
  container.append(grid);
  return grid;
}

function makeRow({ icon, title, detail, meta = "", disabled = false, onClick = null }) {
  const row = $("#menu-row-template").content.firstElementChild.cloneNode(true);
  row.querySelector(".menu-row-icon").textContent = icon;
  row.querySelector("strong").textContent = title;
  row.querySelector("small").textContent = detail;
  row.querySelector(".menu-row-meta").textContent = meta;
  row.disabled = disabled;
  if (onClick) row.addEventListener("click", onClick);
  return row;
}

function empty(container, message) {
  const node = document.createElement("p");
  node.className = "empty-state";
  node.textContent = message;
  container.append(node);
}

function itemIcon(item) {
  if (item.type === "consumable") return "+";
  if (item.equip?.slot === "weapon") return "⚔";
  if (item.equip?.slot === "armor") return "◈";
  return "●";
}

function describeItem(itemId) {
  const item = content.items[itemId] ?? {};
  if (item.type === "consumable") {
    const heal = item.effect?.ratio ? `${Math.round(item.effect.ratio * 100)}% max HP` : `${item.effect?.amount ?? 0} HP`;
    return `Restores ${heal}`;
  }
  if (item.equip) {
    const level = engine.state.itemLevels[itemId];
    const bonus = item.equip.slot === "weapon"
      ? `+${item.equip.level_scaled ? level ?? 1 : item.equip.pwr_bonus ?? 0} PWR`
      : `+${item.equip.level_scaled ? (level ?? 1) * 4 : item.equip.max_hp_bonus ?? 0} max HP`;
    const ability = item.equip.ability?.kind;
    return `${item.equip.weapon_type ?? item.equip.slot} · ${bonus}${ability ? ` · ${ability}` : ""}`;
  }
  if (item.xp_value) return `Smelts into ${item.xp_value} XP when gathered`;
  return item.type ?? "Item";
}

function consumableIds() {
  return Object.keys(engine.state.bag).filter((id) => content.items[id]?.type === "consumable" && engine.state.bag[id] > 0);
}

function openCombat(message) {
  elements.combat.hidden = false;
  elements.combatMessage.textContent = message;
  renderCombat();
  playTone(120, 0.12);
}

function renderCombat() {
  const enemy = engine.combat;
  if (!enemy) return;
  const maxHp = engine.effectiveMaxHp();
  elements.enemyName.textContent = enemy.name;
  elements.enemySprite.textContent = ENEMY_SPRITES[enemy.id] ?? "✹";
  elements.enemyHp.textContent = `${Math.max(0, enemy.hp)} / ${enemy.maxHp} HP`;
  elements.enemyBar.style.width = `${Math.max(0, enemy.hp / enemy.maxHp * 100)}%`;
  elements.heroHp.textContent = `${Math.max(0, engine.state.hp)} / ${maxHp} HP`;
  elements.heroBar.style.width = `${Math.max(0, engine.state.hp / maxHp * 100)}%`;
  elements.combatDistance.textContent = enemy.distance.toUpperCase();
  elements.combatActions.replaceChildren();
  const actions = [
    ["Attack", () => animateCombat("enemy", engine.playerAttack())],
    ["Defend", () => animateCombat("hero", engine.defend())],
    [enemy.distance === "close" ? "Move back" : "Rush in", () => animateCombat("hero", engine.changeDistance())],
    ["Use item", useItemInCombat, !consumableIds().length],
  ];
  actions.forEach(([label, handler, disabled]) => {
    const button = document.createElement("button");
    button.textContent = label;
    button.disabled = Boolean(disabled);
    button.addEventListener("click", handler);
    elements.combatActions.append(button);
  });
}

function animateCombat(target, result) {
  const node = target === "enemy" ? elements.enemySprite : $(".hero-sprite");
  node.classList.remove("flash", "shake");
  requestAnimationFrame(() => node.classList.add(target === "enemy" ? "shake" : "flash"));
  playTone(target === "enemy" ? 260 : 110, 0.06);
  handleCombatResult(result);
}

function useItemInCombat() {
  const itemId = consumableIds()[0];
  if (!itemId) return;
  const use = engine.useItem(itemId);
  if (!use.ok) {
    elements.combatMessage.textContent = use.message;
    return;
  }
  const result = engine.enemyTurn(false, [use.message]);
  handleCombatResult(result);
}

function handleCombatResult(result) {
  elements.combatMessage.textContent = result.message;
  saveState(engine.state);
  render();
  if (result.status === "continue") {
    renderCombat();
    return;
  }
  if (result.status === "victory" && result.dungeon) {
    finishDungeonFloor(result);
    return;
  }
  if (["victory", "defeat", "flee"].includes(result.status)) {
    setTimeout(() => {
      elements.combat.hidden = true;
      setMessage(result.message);
      render();
    }, result.status === "victory" ? 900 : 450);
  }
}

function finishDungeonFloor(result) {
  const context = result.dungeon;
  const dungeon = content.dungeons[context.id];
  const nextFloor = context.floor + 1;
  if (nextFloor < dungeon.floors.length) {
    elements.combatMessage.textContent = `${result.message} Descending to floor ${nextFloor + 1}…`;
    setTimeout(() => {
      const next = engine.startFight(dungeon.floors[nextFloor], {
        difficulty: dungeon.difficulty,
        dungeon: { id: context.id, floor: nextFloor },
      });
      openCombat(next.message);
    }, 1100);
    return;
  }
  const levelGain = engine.gainXp(dungeon.bonus_xp ?? 0);
  const rewards = [];
  (dungeon.reward ?? []).forEach((itemId) => {
    engine.addItem(itemId, 1);
    rewards.push(content.items[itemId]?.name ?? itemId);
  });
  const message = `${result.message} ${dungeon.name} cleared! +${dungeon.bonus_xp ?? 0} XP${rewards.length ? `. Rewards: ${rewards.join(", ")}` : ""}${levelGain ? `. Level ${engine.state.level}!` : ""}.`;
  saveState(engine.state);
  elements.combatMessage.textContent = message;
  setTimeout(() => {
    elements.combat.hidden = true;
    setMessage(message);
    render();
  }, 1300);
}

function playTone(frequency, duration) {
  if (!soundEnabled || !globalThis.AudioContext) return;
  try {
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(.025, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(.001, context.currentTime + duration);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + duration);
  } catch {
    // Sound is optional; browser privacy settings may block it.
  }
}

boot();
