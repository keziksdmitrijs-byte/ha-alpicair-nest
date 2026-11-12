#!/usr/bin/env node
/* Things the panels promise that only a look at their source can check:
 * they run on old wall panel browsers, and the wall panel's menu reaches every setting.
 *
 *   node tests/check_panels.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.join(__dirname, "..", "custom_components", "alpicair_nest");
const main = fs.readFileSync(path.join(root, "frontend", "alpicair-nest-panel.js"), "utf8");
const wall = fs.readFileSync(path.join(root, "frontend", "alpicair-nest-wall.js"), "utf8");
const table = JSON.parse(fs.readFileSync(path.join(root, "registers.json"), "utf8"));
const nestTable = JSON.parse(fs.readFileSync(path.join(root, "registers_nest.json"), "utf8"));
const problems = [];
const code = (source) => source.replace(/\/\*[\s\S]*?\*\//g, "");

const OLD_JS = [
  [/\w\?\.[\w([]/, "optional chaining"], [/\?\?/, "nullish coalescing"], [/Object\.fromEntries/, "Object.fromEntries"],
  [/toggleAttribute/, "toggleAttribute"], [/replaceAll/, "replaceAll"], [/\.flat\(|flatMap/, "flat"], [/matchAll/, "matchAll"],
  [/\.at\(/, ".at()"], [/ResizeObserver/, "ResizeObserver"], [/structuredClone/, "structuredClone"], [/dateStyle/, "dateStyle"],
  [/\bstatic\s+\w+\s*=/, "class fields"], [/\bcatch\s*\{/, "catch without a binding"],
];
for (const [name, source] of [["panel", main], ["wall", wall]]) {
  for (const [pattern, what] of OLD_JS) if (pattern.test(code(source))) problems.push(`${name}: ${what} needs a newer browser`);
}
const OLD_CSS = [
  [/[\s;{]inset:/, "inset"], [/aspect-ratio/, "aspect-ratio"], [/color-mix/, "color-mix"], [/clamp\(/, "clamp()"],
  [/backdrop-filter/, "backdrop-filter"], [/:is\(|:where\(|:has\(/, "newer selectors"], [/:focus-visible/, ":focus-visible"],
  [/(^|[\s;{])gap:/m, "gap (use grid-gap, on grids only)"], [/conic-gradient/, "conic-gradient"],
];
for (const [pattern, what] of OLD_CSS) if (pattern.test(code(wall))) problems.push(`wall: ${what} needs a newer browser`);

const sandbox = {
  URLSearchParams, location: { search: "" }, window: {}, document: {},
  HTMLElement: class {}, customElements: { get: () => null, define: (name, element) => { sandbox.Wall = element; } },
};
vm.runInNewContext(wall, sandbox);
const { TREE, TREE_NEST, TITLES, STRINGS } = sandbox.Wall;

const CLOCK = new Set(["Min", "Hour", "Day", "Date", "Month", "Year"]);
// every setting of a kind of unit is in one menu of that unit's tree, and no menu is empty
const checkTree = (kind, tree, registers) => {
  const leaves = [];
  const ids = new Set();
  const walk = (nodes, service) => {
    for (const node of nodes) {
      const key = node.title || node.id;
      if (!TITLES[key]) problems.push(`${kind} menu: ${node.id} has no title`);
      if (ids.has(node.id)) problems.push(`${kind} menu: ${node.id} is there twice`);
      ids.add(node.id);
      const inside = service || Boolean(node.service);
      if (node.kids) walk(node.kids, inside);
      else if (node.match || node.sections) leaves.push({ id: node.id, match: node.match, sections: node.sections, clock: node.clock, service: inside });
      else if (!node.view) problems.push(`${kind} menu: ${node.id} leads nowhere`);
    }
  };
  walk(tree, false);
  const holds = (leaf, register) =>
    leaf.service === (register.lvl === "service") &&
    (!leaf.sections || leaf.sections.includes(register.sec)) &&
    (!leaf.match || leaf.match.test(register.n));
  const reached = new Map(leaves.map((leaf) => [leaf.id, 0]));
  for (const register of registers) {
    if (CLOCK.has(register.n) || register.n === "Scheduler_Mode") continue;
    const found = leaves.filter((leaf) => holds(leaf, register));
    if (found.length === 0) problems.push(`${kind} menu: ${register.n} (${register.lvl}, ${register.sec}) cannot be reached`);
    if (found.length > 1) problems.push(`${kind} menu: ${register.n} is in ${found.map((leaf) => leaf.id).join(" and ")}`);
    found.forEach((leaf) => reached.set(leaf.id, reached.get(leaf.id) + 1));
  }
  // a leaf that shows the unit's clock need not hold a setting
  for (const leaf of leaves) if (reached.get(leaf.id) === 0 && !leaf.clock) problems.push(`${kind} menu: ${leaf.id} is empty`);
  return leaves;
};
const leaves = checkTree("NEST LS", TREE, table.sp);
const nestLeaves = checkTree("NEST", TREE_NEST, nestTable.sp);

// the home screen's speed control writes to registers it names itself
const settings = new Set(table.sp.map((register) => register.n));
const fanName = sandbox.Wall.prototype._fanName;
for (const strategy of [0, 1, 2]) {
  for (const mode of [1, 2, 3, 4, 5]) {
    for (const fan of [1, 2]) {
      const name = fanName.call({ _sp: { Fans_ControlStrategy: strategy }, _fanStrategy: sandbox.Wall.prototype._fanStrategy }, mode, fan);
      if (!settings.has(name)) problems.push(`fans: ${name} is not a setting`);
    }
  }
}

// a NEST's steps are in percent whatever its fans are held by, and it has no kitchen hood mode
const nestSettings = new Set(nestTable.sp.map((register) => register.n));
for (const mode of [1, 2, 3, 4]) {
  for (const fan of [1, 2]) {
    const name = fanName.call({ _sp: {}, _profile: { model: "nest" }, _fanStrategy: sandbox.Wall.prototype._fanStrategy }, mode, fan);
    if (!nestSettings.has(name)) problems.push(`NEST fans: ${name} is not a setting`);
  }
}

const keys = (object) => Object.keys(object).sort().join(" ");
if (keys(STRINGS.ru) !== keys(STRINGS.lv) || keys(STRINGS.ru) !== keys(STRINGS.en)) {
  const all = new Set([...Object.keys(STRINGS.ru), ...Object.keys(STRINGS.lv), ...Object.keys(STRINGS.en)]);
  for (const key of all) for (const lang of ["ru", "lv", "en"]) if (!(key in STRINGS[lang])) problems.push(`strings: ${lang} lacks ${key}`);
}

if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log(`ok: NEST LS ${table.sp.length} settings reached through ${leaves.length} menus, NEST ${nestTable.sp.length} through ${nestLeaves.length}`);
