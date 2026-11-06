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
const { TREE, TITLES, STRINGS } = sandbox.Wall;

const leaves = [];
const walk = (nodes, service) => {
  for (const node of nodes) {
    const key = node.title || node.id;
    if (!TITLES[key]) problems.push(`menu: ${node.id} has no title`);
    const inside = service || Boolean(node.service);
    if (node.kids) walk(node.kids, inside);
    else if (node.match) leaves.push({ id: node.id, match: node.match, service: inside });
    else if (!node.view) problems.push(`menu: ${node.id} leads nowhere`);
  }
};
walk(TREE, false);

const CLOCK = new Set(["Min", "Hour", "Day", "Date", "Month", "Year"]);
const reached = new Map(leaves.map((leaf) => [leaf.id, 0]));
for (const register of table.sp) {
  if (CLOCK.has(register.n) || register.n === "Scheduler_Mode") continue;
  const found = leaves.filter((leaf) => leaf.service === (register.lvl === "service") && leaf.match.test(register.n));
  if (found.length === 0) problems.push(`menu: ${register.n} (${register.lvl}) cannot be reached`);
  if (found.length > 1) problems.push(`menu: ${register.n} is in ${found.map((leaf) => leaf.id).join(" and ")}`);
  found.forEach((leaf) => reached.set(leaf.id, reached.get(leaf.id) + 1));
}
for (const [id, count] of reached) if (count === 0) problems.push(`menu: ${id} is empty`);

// the home screen's speed control writes to registers it names itself
const settings = new Set(table.sp.map((register) => register.n));
const fanName = sandbox.Wall.prototype._fanName;
for (const strategy of [0, 1, 2]) {
  for (const mode of [1, 2, 3, 4, 5]) {
    for (const fan of [1, 2]) {
      const name = fanName.call({ _sp: { Fans_ControlStrategy: strategy } }, mode, fan);
      if (!settings.has(name)) problems.push(`fans: ${name} is not a setting`);
    }
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
console.log(`ok: ${table.sp.length} settings reached through ${leaves.length} menus`);
