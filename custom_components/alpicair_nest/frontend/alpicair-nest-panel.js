/* AlpicAir NEST panel for Home Assistant. No build step, no dependencies.
 *
 * Wall panels run old browsers: the NSPanel Pro has Android 8.1 and its WebView can be Chromium 61.
 * So this file stays within ES2018, without ?. and ??, and every newer CSS feature has a fallback.
 */

const DOMAIN = "alpicair_nest";
const TABS = ["overview", "settings", "schedule", "data", "service", "faults"];
const QUERY = new URLSearchParams(location.search);
// a square screen of about this many pixels gets the layout drawn for it, scaled to fit
const WALL_SIZE = 480;
const WALL_LIMIT = 800;
const WALL_LANGUAGE = "input_select.nspanel_language";
const DAYS_IN_WEEK = 7;
const EVENTS_IN_DAY = 10;
const TARGET_STEP = 0.5;
const SAVE_PAUSE = 800;

const STRINGS = {
  ru: {
    title: "AlpicAir NEST",
    tabs: { overview: "Обзор", settings: "Настройки", schedule: "Расписание", data: "Данные", service: "Сервис", faults: "Ошибки" },
    online: "На связи", offline: "Нет связи с установкой", loading: "Загрузка…",
    noUnit: "Установка не подключена. Добавьте её в Настройки → Устройства и службы.",
    faultsActive: (n) => `Активных неисправностей: ${n}`, showFaults: "Подробнее",
    outdoor: "С улицы", supply: "В помещения", extract: "Из помещений", exhaust: "Выброс",
    recovery: "рекуперация", supplyFan: "Приток", exhaustFan: "Вытяжка",
    control: "Управление", scheduleMode: "По расписанию", off: "Выключить",
    modes: ["Ожидание", "Никого нет", "Эконом", "Комфорт", "Буст", "Вытяжка"],
    now: "Сейчас", manual: "вручную", onSchedule: "по расписанию", temporary: "временный режим",
    targetSupply: "Уставка притока", targetExtract: "Уставка вытяжки",
    phase: "Что делает", rotor: "Ротор", bypass: "Байпас", filter: "Фильтр",
    filterReset: "Сбросить таймер", filterResetAsk: "Сбросить таймер фильтра? Делайте это после замены фильтра.",
    filterLeft: "до замены", presentTarget: "Уставка сейчас", hours: "Моточасы", humidity: "Влажность", co2: "CO₂",
    freeCooling: "Идёт свободное охлаждение", deicing: "Идёт оттайка", boostLeft: (n) => `Буст ещё ${n} мин`,
    search: "Поиск", nothingFound: "Ничего не найдено", adminOnly: "Менять могут только администраторы",
    run: "Выполнить", yes: "Да", no: "Нет", on: "Вкл", offState: "Выкл", cancel: "Отмена", ok: "Продолжить",
    saved: "Сохранено", clock: "Часы установки", syncClock: "Поставить время Home Assistant",
    week: "Неделя", dayNames: ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
    dayShort: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    scheduleModes: ["Не используется", "Ожидание", "Никого нет", "Эконом", "Комфорт", "Буст"],
    scheduleOff: "Установка сейчас в ручном режиме, расписание не выполняется.", scheduleOn: "Включить расписание",
    addEvent: "Добавить событие", removeEvent: "Удалить", save: "Сохранить", revert: "Вернуть", noEvents: "На этот день событий нет.",
    copyTo: "Скопировать на", copy: "Скопировать", startsAt: "Начало", mode: "Режим", temperature: "Температура",
    locked: "Сервисные настройки закрыты", lockedText: "Введите сервисный PIN установки. Он сверяется с установкой и нигде не сохраняется.",
    pin: "Сервисный PIN", unlock: "Открыть", lock: "Закрыть доступ", unlockedFor: (t) => `Доступ открыт ещё ${t}`,
    needAdmin: "Сервисные настройки доступны только администраторам.",
    connection: "Подключение", host: "Адрес", port: "Порт", unitId: "Адрес Modbus", framing: "Протокол",
    mac: "MAC", ip: "IP установки", firmware: "Прошивка", bootloader: "Загрузчик", eeprom: "Записей в EEPROM",
    factory: "заводское", dangerAsk: "Неверное значение может остановить установку или оборвать связь с ней. Продолжить?",
    dangerPress: "Команда выполнится сразу и может остановить установку. Продолжить?",
    activeFaults: "Сейчас", noFaults: "Неисправностей нет", resetErrors: "Сбросить ошибки", history: "История",
    noHistory: "История пуста", clearHistory: "Очистить", clearHistoryAsk: "Очистить историю? Она хранится только в Home Assistant.",
    appeared: "появилась", cleared: "прошла", kinds: { error: "Ошибка", warning: "Предупреждение", alarm: "Тревога" },
    rawWords: "Слова состояния", unnamedBit: (w, b) => `${w}, бит ${b}`,
    errors: {
      forbidden: "Для этого нужны права администратора",
      service_locked: "Сервисный доступ закрыт, введите PIN ещё раз",
      wrong_pin: "Неверный PIN",
      too_many_tries: (s) => `Слишком много попыток, подождите ${s} с`,
      unit_error: "Установка не ответила",
      invalid_value: "Недопустимое значение",
      not_found: "Такой настройки нет",
      other: "Не получилось",
    },
    units: { rpm: "об/мин", "m³/h": "м³/ч", d: "дн.", h: "ч", min: "мин", s: "с", Pa: "Па", V: "В", mA: "мА" },
    sections: {
      connection: "Подключение", operation: "Работа", temperature: "Температура", air_quality: "Качество воздуха",
      free_cooling: "Свободное охлаждение", fans: "Вентиляторы", temporary: "Временные режимы", cooker_hood: "Кухонная вытяжка",
      time: "Дата и время", schedule: "Расписание", system: "Система", fan_hw: "Вентиляторы: оборудование",
      temp_sensors: "Датчики температуры", pressure: "Давление", analog_inputs: "Аналоговые входы", digital_inputs: "Цифровые входы",
      dampers: "Клапаны", fire: "Пожарная защита", coils: "Нагрев и охлаждение", recovery: "Рекуперация", network: "Сеть",
      fieldbus: "Шина", maintenance: "Обслуживание", air: "Воздух", inputs: "Входы", device: "Устройство",
    },
  },
  en: {
    title: "AlpicAir NEST",
    tabs: { overview: "Overview", settings: "Settings", schedule: "Schedule", data: "Data", service: "Service", faults: "Faults" },
    online: "Online", offline: "The unit is not responding", loading: "Loading…",
    noUnit: "No unit is connected. Add one under Settings → Devices & services.",
    faultsActive: (n) => `Active faults: ${n}`, showFaults: "Details",
    outdoor: "From outside", supply: "To rooms", extract: "From rooms", exhaust: "Exhaust",
    recovery: "recovery", supplyFan: "Supply", exhaustFan: "Extract",
    control: "Control", scheduleMode: "Schedule", off: "Turn off",
    modes: ["Standby", "Unoccupied", "Economy", "Comfort", "Boost", "Kitchen hood"],
    now: "Now", manual: "manual", onSchedule: "on schedule", temporary: "temporary mode",
    targetSupply: "Supply target", targetExtract: "Extract target",
    phase: "Doing now", rotor: "Rotor", bypass: "Bypass", filter: "Filter",
    filterReset: "Reset timer", filterResetAsk: "Reset the filter timer? Do this after changing the filter.",
    filterLeft: "until replacement", presentTarget: "Target now", hours: "Running hours", humidity: "Humidity", co2: "CO₂",
    freeCooling: "Free cooling is running", deicing: "De-icing is running", boostLeft: (n) => `Boost for ${n} more min`,
    search: "Search", nothingFound: "Nothing found", adminOnly: "Only administrators can change this",
    run: "Run", yes: "Yes", no: "No", on: "On", offState: "Off", cancel: "Cancel", ok: "Continue",
    saved: "Saved", clock: "Unit clock", syncClock: "Set to Home Assistant time",
    week: "Week", dayNames: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    dayShort: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    scheduleModes: ["Not used", "Standby", "Unoccupied", "Economy", "Comfort", "Boost"],
    scheduleOff: "The unit is in manual control, so the schedule is not running.", scheduleOn: "Turn the schedule on",
    addEvent: "Add event", removeEvent: "Remove", save: "Save", revert: "Revert", noEvents: "No events on this day.",
    copyTo: "Copy to", copy: "Copy", startsAt: "Start", mode: "Mode", temperature: "Temperature",
    locked: "Service settings are locked", lockedText: "Enter the unit's service PIN. It is checked against the unit and not stored.",
    pin: "Service PIN", unlock: "Unlock", lock: "Lock", unlockedFor: (t) => `Unlocked for ${t}`,
    needAdmin: "Service settings are for administrators only.",
    connection: "Connection", host: "Address", port: "Port", unitId: "Modbus unit ID", framing: "Framing",
    mac: "MAC", ip: "Unit IP", firmware: "Firmware", bootloader: "Bootloader", eeprom: "EEPROM writes",
    factory: "factory", dangerAsk: "A wrong value can stop the unit or cut the connection to it. Continue?",
    dangerPress: "This runs at once and can stop the unit. Continue?",
    activeFaults: "Now", noFaults: "No faults", resetErrors: "Reset errors", history: "History",
    noHistory: "No history yet", clearHistory: "Clear", clearHistoryAsk: "Clear the history? It is kept only in Home Assistant.",
    appeared: "appeared", cleared: "cleared", kinds: { error: "Error", warning: "Warning", alarm: "Alarm" },
    rawWords: "Status words", unnamedBit: (w, b) => `${w}, bit ${b}`,
    errors: {
      forbidden: "This takes an administrator",
      service_locked: "Service access has closed, enter the PIN again",
      wrong_pin: "Wrong PIN",
      too_many_tries: (s) => `Too many tries, wait ${s} s`,
      unit_error: "The unit did not answer",
      invalid_value: "That value is not allowed",
      not_found: "No such setting",
      other: "That did not work",
    },
    units: { d: "days" },
    sections: {
      connection: "Connection", operation: "Operation", temperature: "Temperature", air_quality: "Air quality",
      free_cooling: "Free cooling", fans: "Fans", temporary: "Temporary modes", cooker_hood: "Cooker hood",
      time: "Date and time", schedule: "Schedule", system: "System", fan_hw: "Fan hardware",
      temp_sensors: "Temperature sensors", pressure: "Pressure", analog_inputs: "Analog inputs", digital_inputs: "Digital inputs",
      dampers: "Dampers", fire: "Fire protection", coils: "Heating and cooling", recovery: "Heat recovery", network: "Network",
      fieldbus: "Fieldbus", maintenance: "Maintenance", air: "Air", inputs: "Inputs", device: "Device",
    },
  },
};

STRINGS.lv = {
  ...STRINGS.en,
  tabs: { overview: "Pārskats", settings: "Iestatījumi", schedule: "Grafiks", data: "Dati", service: "Serviss", faults: "Kļūdas" },
  online: "Savienots", offline: "Iekārta neatbild", loading: "Ielādē…",
  noUnit: "Iekārta nav pievienota. Pievienojiet to sadaļā Iestatījumi → Ierīces un pakalpojumi.",
  faultsActive: (n) => `Aktīvie bojājumi: ${n}`, showFaults: "Sīkāk",
  outdoor: "No ārpuses", supply: "Uz telpām", extract: "No telpām", exhaust: "Izmešana",
  recovery: "atguve", supplyFan: "Pieplūde", exhaustFan: "Nosūce",
  control: "Vadība", scheduleMode: "Pēc grafika", off: "Izslēgt",
  modes: ["Gaidstāve", "Neviena nav", "Ekonomija", "Komforts", "Boost", "Tvaika nosūcējs"],
  now: "Tagad", manual: "manuāli", onSchedule: "pēc grafika", temporary: "pagaidu režīms",
  targetSupply: "Pieplūdes iestatījums", targetExtract: "Nosūces iestatījums",
  phase: "Darbība", rotor: "Rotors", bypass: "Apvads", filter: "Filtrs",
  filterReset: "Atiestatīt taimeri", filterResetAsk: "Atiestatīt filtra taimeri? Dariet to pēc filtra nomaiņas.",
  filterLeft: "līdz nomaiņai", presentTarget: "Pašreizējais iestatījums", hours: "Darba stundas", humidity: "Mitrums",
  search: "Meklēt", nothingFound: "Nekas nav atrasts", adminOnly: "Mainīt var tikai administratori",
  run: "Izpildīt", yes: "Jā", no: "Nē", on: "Iesl.", offState: "Izsl.", cancel: "Atcelt", ok: "Turpināt",
  saved: "Saglabāts", clock: "Iekārtas pulkstenis", syncClock: "Iestatīt Home Assistant laiku",
  week: "Nedēļa", dayNames: ["Pirmdiena", "Otrdiena", "Trešdiena", "Ceturtdiena", "Piektdiena", "Sestdiena", "Svētdiena"],
  dayShort: ["Pr", "Ot", "Tr", "Ce", "Pk", "Se", "Sv"],
  scheduleModes: ["Nav izmantots", "Gaidstāve", "Neviena nav", "Ekonomija", "Komforts", "Boost"],
  scheduleOff: "Iekārta ir manuālā vadībā, grafiks nedarbojas.", scheduleOn: "Ieslēgt grafiku",
  addEvent: "Pievienot notikumu", removeEvent: "Dzēst", save: "Saglabāt", revert: "Atjaunot", noEvents: "Šajā dienā notikumu nav.",
  copyTo: "Kopēt uz", copy: "Kopēt", startsAt: "Sākums", mode: "Režīms", temperature: "Temperatūra",
  locked: "Servisa iestatījumi ir slēgti", lockedText: "Ievadiet iekārtas servisa PIN. Tas tiek salīdzināts ar iekārtu un netiek saglabāts.",
  pin: "Servisa PIN", unlock: "Atvērt", lock: "Slēgt", unlockedFor: (t) => `Atvērts vēl ${t}`,
  needAdmin: "Servisa iestatījumi ir pieejami tikai administratoriem.",
  connection: "Savienojums", host: "Adrese", port: "Ports", unitId: "Modbus adrese",
  activeFaults: "Tagad", noFaults: "Bojājumu nav", resetErrors: "Atiestatīt kļūdas", history: "Vēsture",
  noHistory: "Vēstures nav", clearHistory: "Notīrīt", clearHistoryAsk: "Notīrīt vēsturi? Tā glabājas tikai Home Assistant.",
  appeared: "parādījās", cleared: "pazuda", kinds: { error: "Kļūda", warning: "Brīdinājums", alarm: "Trauksme" },
};

const or = (value, other) => (value === null || value === undefined ? other : value);

const byName = (items) => {
  const table = {};
  items.forEach((item) => {
    table[item.name] = item;
  });
  return table;
};

const esc = (text) =>
  String(or(text, "")).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const ICONS = {
  overview: "M4 11l8-7 8 7v9h-5v-6H9v6H4z",
  settings: "M3 7h11M18 7h3M3 17h3M10 17h11M16 5v4M8 15v4",
  schedule: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 7v5l3 2",
  data: "M5 20V11M12 20V4M19 20v-7",
  service: "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5z",
  faults: "M12 4l9 16H3zM12 10v5M12 17.5v.5",
};

const STYLE = `
:host {
  --nest-fresh: #1f88d6;
  --nest-stale: #d9772b;
  --nest-card: var(--ha-card-background, var(--card-background-color, #fff));
  --nest-text: var(--primary-text-color, #1c1c1c);
  --nest-muted: var(--secondary-text-color, #5f6368);
  --nest-line: var(--divider-color, rgba(0, 0, 0, .12));
  --nest-accent: var(--primary-color, #03a9f4);
  --nest-on-accent: var(--text-primary-color, #fff);
  --nest-error: var(--error-color, #db4437);
  --nest-warning: var(--warning-color, #e6a100);
  --nest-success: var(--success-color, #2e9d57);
  --nest-soft: var(--secondary-background-color, rgba(127, 127, 127, .14));
  display: block; min-height: 100%; box-sizing: border-box;
  background: var(--primary-background-color, #f5f5f5); color: var(--nest-text);
  font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, system-ui, sans-serif));
  font-size: 14px; line-height: 1.4;
}
* { box-sizing: border-box; }
header {
  position: sticky; top: 0; z-index: 3; display: flex; align-items: center; gap: 8px;
  height: var(--header-height, 56px); padding: 0 12px;
  background: var(--app-header-background-color, var(--nest-accent)); color: var(--app-header-text-color, #fff);
}
header h1 { flex: 1; margin: 0; font-size: 20px; font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.menu { display: none; width: 40px; height: 40px; padding: 8px; border: 0; border-radius: 50%; background: none; color: inherit; cursor: pointer; }
:host([narrow]) .menu { display: block; }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; white-space: nowrap; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: var(--nest-success); box-shadow: 0 0 0 2px rgba(255, 255, 255, .55); }
.status.bad .dot { background: var(--nest-error); }
header select { max-width: 40vw; padding: 4px; border-radius: 6px; }
nav.tabs {
  position: sticky; top: var(--header-height, 56px); z-index: 2; display: flex; gap: 2px; padding: 0 8px; overflow-x: auto;
  background: var(--nest-card); border-bottom: 1px solid var(--nest-line); scrollbar-width: none;
}
nav.tabs button {
  position: relative; flex: none; padding: 13px 14px; border: 0; background: none; color: var(--nest-muted);
  font: inherit; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent;
}
nav.tabs button[aria-selected="true"] { color: var(--nest-accent); border-bottom-color: var(--nest-accent); }
.count { display: inline-block; min-width: 18px; margin-left: 4px; padding: 0 5px; border-radius: 9px; background: var(--nest-error); color: #fff; font-size: 12px; line-height: 18px; text-align: center; }
main { max-width: 1120px; margin: 0 auto; padding: 16px; }
:host([narrow]) main { padding: 12px; }
.card { padding: 16px; background: var(--nest-card); border-radius: var(--ha-card-border-radius, 12px); border: 1px solid var(--ha-card-border-color, var(--nest-line)); }
.card + .card { margin-top: 12px; }
h2 { margin: 0 0 10px; font-size: 16px; font-weight: 500; }
.muted { color: var(--nest-muted); }
.small { font-size: 12px; }
.banner { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; padding: 10px 14px; border-radius: 10px; background: var(--nest-card); background: color-mix(in srgb, var(--nest-error) 14%, var(--nest-card)); border: 1px solid var(--nest-error); }
.banner.info { background: var(--nest-card); background: color-mix(in srgb, var(--nest-warning) 14%, var(--nest-card)); border-color: var(--nest-warning); }
.banner > span { flex: 1; }
button.btn, input, select { font: inherit; color: inherit; }
button.btn {
  min-height: 36px; padding: 6px 14px; border: 1px solid var(--nest-line); border-radius: 8px;
  background: var(--nest-card); color: var(--nest-text); cursor: pointer;
}
button.btn:hover:not(:disabled) { border-color: var(--nest-accent); }
button.btn.primary { background: var(--nest-accent); border-color: var(--nest-accent); color: var(--nest-on-accent); }
button.btn.danger { border-color: var(--nest-error); color: var(--nest-error); }
button:disabled { opacity: .5; cursor: default; }
input, select { min-height: 36px; padding: 6px 8px; border: 1px solid var(--nest-line); border-radius: 8px; background: var(--nest-card); }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 2px solid var(--nest-accent); outline-offset: 1px; }

/* overview */
.overview { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: 12px; align-items: start; }
:host([narrow]) .overview { grid-template-columns: minmax(0, 1fr); }
.overview .card + .card { margin-top: 0; }
.span { grid-column: 1 / -1; }
.scheme { position: relative; height: 0; padding-bottom: 57.7%; min-height: 230px; width: 100%; }
.scheme svg { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
.port { position: absolute; display: flex; flex-direction: column; min-width: 92px; padding: 2px 6px; background: var(--nest-card); border-radius: 6px; }
.port b { font-size: 22px; font-weight: 500; line-height: 1.2; white-space: nowrap; }
.port span { color: var(--nest-muted); font-size: 12px; white-space: nowrap; }
.port.tl { left: 0; top: 0; } .port.bl { left: 0; bottom: 0; }
.port.tr { right: 0; top: 0; text-align: right; } .port.br { right: 0; bottom: 0; text-align: right; }
.flow { fill: none; stroke-width: 7; stroke-linecap: round; }
.flow.fresh { stroke: var(--nest-fresh); } .flow.stale { stroke: var(--nest-stale); }
.dash { fill: none; stroke: #fff; stroke-opacity: .75; stroke-width: 2; stroke-dasharray: 3 15; stroke-linecap: round; }
.running .dash { animation: move 1.1s linear infinite; }
@keyframes move { to { stroke-dashoffset: -18; } }
.body { fill: var(--secondary-background-color, rgba(127, 127, 127, .08)); stroke: var(--nest-line); stroke-width: 2; }
.core { fill: var(--nest-card); stroke: var(--nest-muted); stroke-width: 2; }
.core-text { fill: var(--nest-text); font-size: 20px; font-weight: 500; text-anchor: middle; }
.core-sub { fill: var(--nest-muted); font-size: 11px; text-anchor: middle; }
:host([narrow]) .core-text { font-size: 30px; transform: translateY(9px); }
:host([narrow]) .core-sub { display: none; }
.fan { fill: var(--nest-card); stroke: var(--nest-muted); stroke-width: 2; }
.blades { fill: var(--nest-muted); transform-box: fill-box; transform-origin: center; }
.running .blades { animation: spin var(--spin, 1.5s) linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .running .dash, .running .blades { animation: none; } }
.modes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }
.modes .wide { grid-column: 1 / -1; }
.modes button { min-height: 44px; padding: 6px; }
.modes button[aria-pressed="true"] { background: var(--nest-accent); border-color: var(--nest-accent); color: var(--nest-on-accent); }
.now { margin: 10px 0 0; color: var(--nest-muted); }
.target { display: flex; align-items: center; gap: 10px; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--nest-line); }
.target > div { flex: 1; text-align: center; }
.target b { display: block; font-size: 30px; font-weight: 400; line-height: 1.15; }
.target button { width: 48px; height: 48px; font-size: 22px; padding: 0; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.tile { padding: 12px 14px; background: var(--nest-card); border-radius: var(--ha-card-border-radius, 12px); border: 1px solid var(--ha-card-border-color, var(--nest-line)); min-width: 0; }
.tile span { display: block; color: var(--nest-muted); font-size: 12px; }
.tile b { display: block; font-size: 20px; font-weight: 500; line-height: 1.3; }
.tile small { display: block; color: var(--nest-muted); font-size: 12px; }
.tile .btn { margin-top: 8px; min-height: 30px; padding: 3px 10px; font-size: 12px; }
.bar { height: 6px; margin-top: 6px; border-radius: 3px; background: var(--nest-line); overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--nest-success); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { padding: 3px 10px; border-radius: 12px; background: var(--secondary-background-color, rgba(127, 127, 127, .12)); font-size: 12px; }

/* register lists */
.browser { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 12px; align-items: start; }
:host([narrow]) .browser { grid-template-columns: minmax(0, 1fr); }
.sections { display: flex; flex-direction: column; gap: 2px; position: sticky; top: calc(var(--header-height, 56px) + 60px); }
:host([narrow]) .sections { position: static; flex-direction: row; overflow-x: auto; padding-bottom: 4px; scrollbar-width: thin; }
.sections button { flex: none; display: flex; justify-content: space-between; gap: 8px; padding: 8px 10px; border: 0; border-radius: 8px; background: none; color: var(--nest-text); font: inherit; text-align: left; cursor: pointer; }
.sections button[aria-current="true"] { background: var(--nest-soft); background: color-mix(in srgb, var(--nest-accent) 16%, transparent); color: var(--nest-accent); font-weight: 500; }
.sections span { color: var(--nest-muted); font-weight: 400; }
.finder { width: 100%; margin-bottom: 12px; }
.rows { min-width: 0; padding: 4px 16px; }
.rows h3 { margin: 14px 0 4px; color: var(--nest-muted); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: .04em; }
.row { display: flex; align-items: center; gap: 12px; min-height: 52px; padding: 7px 0; border-bottom: 1px solid var(--nest-line); }
.row:last-child { border-bottom: 0; }
.row-text { flex: 1; min-width: 0; word-break: break-word; overflow-wrap: anywhere; }
.row-meta { color: var(--nest-muted); font-size: 12px; }
.row-control { display: flex; align-items: center; justify-content: flex-end; gap: 6px; flex: none; max-width: 60%; }
.row-control input[type="number"] { width: 96px; text-align: right; }
.row-control select { max-width: 200px; }
.row-state { width: 16px; text-align: center; font-size: 14px; }
.row-state.ok { color: var(--nest-success); } .row-state.bad { color: var(--nest-error); }
.unit { color: var(--nest-muted); font-size: 12px; min-width: 34px; }
.value { font-variant-numeric: tabular-nums; text-align: right; }
.toggle { position: relative; width: 44px; height: 24px; flex: none; }
.toggle input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; margin: 0; min-height: 0; opacity: 0; cursor: pointer; }
.toggle i { position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 12px; background: var(--nest-line); pointer-events: none; transition: background .15s; }
.toggle i::after { content: ""; position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%; background: #fff; box-shadow: 0 1px 2px rgba(0, 0, 0, .3); transition: left .15s; }
.toggle input:checked + i { background: var(--nest-accent); }
.toggle input:checked + i::after { left: 23px; }
.toggle input:disabled + i { opacity: .5; }
.toggle input:focus-visible + i { outline: 2px solid var(--nest-accent); outline-offset: 1px; }
.lamp { display: inline-block; width: 10px; height: 10px; margin-right: 6px; border-radius: 50%; background: var(--nest-line); }
.lamp.on { background: var(--nest-success); }
.empty { padding: 24px 0; color: var(--nest-muted); text-align: center; }

/* schedule */
.week { display: grid; gap: 4px; }
.week button { display: grid; grid-template-columns: 36px minmax(0, 1fr); align-items: center; gap: 8px; padding: 2px; border: 0; border-radius: 6px; background: none; color: inherit; font: inherit; cursor: pointer; text-align: left; }
.week button[aria-current="true"] { background: var(--nest-soft); background: color-mix(in srgb, var(--nest-accent) 14%, transparent); }
.line { position: relative; height: 18px; border-radius: 4px; background: var(--nest-line); overflow: hidden; }
.line i { position: absolute; top: 0; bottom: 0; }
.m1 { background: #8d939c; } .m2 { background: #7fb2dd; } .m3 { background: #4c9f70; } .m4 { background: #e0a23c; } .m5 { background: #d9562b; }
.hours { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 8px; color: var(--nest-muted); font-size: 11px; }
.hours div { display: flex; justify-content: space-between; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 10px; font-size: 12px; color: var(--nest-muted); }
.legend i { display: inline-block; width: 10px; height: 10px; margin-right: 4px; border-radius: 2px; }
.event { display: grid; grid-template-columns: 120px minmax(0, 1fr) 96px auto; gap: 8px; align-items: center; padding: 6px 0; border-bottom: 1px solid var(--nest-line); }
.event-head { padding: 0 0 4px; color: var(--nest-muted); font-size: 12px; }
.event input, .event select { width: 100%; }
:host([narrow]) .event { grid-template-columns: 112px minmax(0, 1fr) 58px 36px; gap: 4px; }
:host([narrow]) .event .btn { padding: 0; width: 36px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; }
.grow { flex: 1; }
.days { display: flex; flex-wrap: wrap; gap: 6px; }
.days label { display: inline-flex; align-items: center; gap: 4px; }
.days input { min-height: 0; }

/* service */
.lockbox { max-width: 380px; margin: 32px auto; text-align: center; }
.lockbox form { display: flex; gap: 8px; margin-top: 14px; }
.lockbox input { flex: 1; min-width: 0; text-align: center; font-size: 18px; letter-spacing: .2em; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px 16px; }
.facts div span { display: block; color: var(--nest-muted); font-size: 12px; }

/* faults */
.fault { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--nest-line); }
.fault:last-child { border-bottom: 0; }
.fault > span:nth-child(2) { flex: 1; min-width: 0; word-break: break-word; overflow-wrap: anywhere; }
.kind { flex: none; padding: 2px 8px; border-radius: 10px; font-size: 12px; color: #fff; background: var(--nest-error); }
.kind.warning { background: var(--nest-warning); color: #000; }
.kind.alarm { background: var(--nest-stale); }
.kind.gone { background: var(--nest-line); color: var(--nest-muted); }
.words { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px 16px; font-family: var(--code-font-family, monospace); font-size: 12px; }

.tab-icon { display: none; }
.stepper { display: none; }

/* square wall panel: everything on one 480 x 480 screen, drawn for fingers */
:host([compact]) { display: flex; flex-direction: column; min-height: 0; overflow: hidden; font-size: 15px; }
:host([compact]) header { position: static; flex: none; height: 40px; padding: 0 8px 0 0; }
:host([compact]) header h1 { margin-left: 2px; font-size: 15px; font-weight: 500; }
:host([compact]) .menu { display: block; flex: none; }
:host([compact]) .status { margin-left: 8px; }
:host([compact]) .status span { display: none; }
:host([compact]) .status.bad span { display: inline; }
:host([compact]) nav.tabs {
  position: static; order: 3; flex: none; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr));
  height: 54px; padding: 0; overflow: hidden; border-bottom: 0; border-top: 1px solid var(--nest-line);
}
:host([compact]) nav.tabs button {
  display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 0; padding: 2px 0 0;
  border-bottom: 0; font-size: 11px; font-weight: 400; white-space: nowrap;
}
:host([compact]) .tab-icon { display: block; width: 24px; height: 24px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
:host([compact]) .count { position: absolute; top: 2px; left: 50%; margin-left: 8px; min-width: 16px; padding: 0 4px; font-size: 11px; line-height: 16px; }
:host([compact]) main { flex: 1; min-height: 0; width: 100%; max-width: none; padding: 6px; overflow-y: auto; -webkit-overflow-scrolling: touch; }
:host([compact]) .card { padding: 8px 10px; }
:host([compact]) .card + .card { margin-top: 6px; }
:host([compact]) .overview { grid-template-columns: minmax(0, 1fr); gap: 6px; grid-gap: 6px; }
:host([compact]) .overview .card + .card { margin-top: 0; }
:host([compact]) #faults-banner, :host([compact]) #chips, :host([compact]) #now, :host([compact]) .control h2 { display: none !important; }
:host([compact]) .overview .card:first-child { padding: 4px 8px; }
:host([compact]) .scheme { height: 122px; min-height: 0; padding-bottom: 0; }
:host([compact]) .port { min-width: 0; padding: 0 2px; }
:host([compact]) .port b { font-size: 20px; }
:host([compact]) .core-text { font-size: 26px; transform: translateY(7px); }
:host([compact]) .core-sub { display: none; }
:host([compact]) .control { display: flex; flex-direction: column; padding: 0; background: none; border: 0; }
:host([compact]) .target { order: -1; height: 52px; margin: 0 0 6px; padding: 0; border-top: 0; }
:host([compact]) .target > div { margin: 0 8px; }
:host([compact]) .target b { font-size: 26px; }
:host([compact]) .target button { width: 64px; height: 52px; flex: none; }
:host([compact]) .modes { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; grid-gap: 6px; }
:host([compact]) .modes .wide { grid-column: 1 / -1; }
:host([compact]) .modes button { min-height: 54px; padding: 4px; font-size: 15px; }
:host([compact]) .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; grid-gap: 6px; }
:host([compact]) .tile { padding: 8px; }
:host([compact]) .tile b { font-size: 17px; }
:host([compact]) .finder { display: none; }
:host([compact]) .browser { grid-template-columns: minmax(0, 1fr); gap: 6px; grid-gap: 6px; }
:host([compact]) .sections { position: static; flex-direction: row; overflow-x: auto; padding-bottom: 2px; }
:host([compact]) .sections button { min-height: 44px; padding: 8px 12px; align-items: center; }
:host([compact]) .sections span { margin-left: 8px; }
:host([compact]) .rows { padding: 2px 10px; }
:host([compact]) .row { min-height: 60px; }
:host([compact]) .row-control { max-width: 66%; gap: 0; }
:host([compact]) .row-control > * + * { margin-left: 4px; }
:host([compact]) .row-control input[type="number"] { width: 72px; height: 44px; padding: 4px; text-align: center; }
:host([compact]) .row-control select { height: 44px; max-width: 190px; }
:host([compact]) .stepper { display: block; width: 44px; min-height: 44px; padding: 0; font-size: 20px; }
:host([compact]) .unit { min-width: 0; }
:host([compact]) .event { grid-template-columns: 112px minmax(0, 1fr) 58px 40px; gap: 4px; grid-gap: 4px; }
:host([compact]) .event .btn { width: 40px; padding: 0; }
:host([compact]) .event input, :host([compact]) .event select { height: 44px; }
:host([compact]) .actions { gap: 0; margin-top: 8px; }
:host([compact]) .actions > * { margin: 0 8px 6px 0; }
:host([compact]) .btn { min-height: 44px; }
:host([compact]) .lockbox { margin: 8px auto; }
:host([compact]) .toast { bottom: 62px; }

dialog { max-width: 420px; padding: 20px; border: 0; border-radius: 12px; background: var(--nest-card); color: var(--nest-text); }
dialog::backdrop { background: rgba(0, 0, 0, .45); }
dialog form { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.toast { position: fixed; left: 50%; bottom: 24px; z-index: 5; max-width: calc(100vw - 32px); padding: 10px 16px; border-radius: 8px; background: #2b2b2b; color: #fff; transform: translateX(-50%); }
`;

class AlpicAirNestPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    const hash = location.hash.slice(1);
    this._tab = TABS.includes(hash) ? hash : "overview";
    this._dp = {};
    this._sp = {};
    this._status = { available: true, virtual: {}, faults: [], words: {} };
    this._section = {};
    this._find = "";
    this._day = 0;
    this._token = null;
    this._tokenUntil = 0;
    this._pending = {};
    this._stepTimers = {};
    this._targetTimer = null;
    this._onResize = () => this._fit();
    this._onHash = () => {
      const tab = location.hash.slice(1);
      if (TABS.includes(tab) && tab !== this._tab) this._openTab(tab);
    };
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
    this.shadowRoot.addEventListener("input", (event) => this._onInput(event));
    this.shadowRoot.addEventListener("submit", (event) => this._onSubmit(event));
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._started && this.isConnected) this._start();
  }

  get hass() {
    return this._hass;
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._fit();
  }

  set panel(_value) {}

  set route(_value) {}

  connectedCallback() {
    if (this._hass && !this._started) this._start();
    this._clock = setInterval(() => this._tick(), 1000);
    window.addEventListener("hashchange", this._onHash);
    window.addEventListener("resize", this._onResize);
    this._fit();
  }

  disconnectedCallback() {
    clearInterval(this._clock);
    window.removeEventListener("hashchange", this._onHash);
    window.removeEventListener("resize", this._onResize);
    this._leave();
    this._started = false;
  }

  _leave() {
    if (this._unsubscribe) this._unsubscribe.then((off) => off()).catch(() => {});
    this._unsubscribe = null;
  }

  // layout

  _setAttribute(name, on) {
    if (on) this.setAttribute(name, "");
    else this.removeAttribute(name);
  }

  _fit() {
    const parent = this.parentElement || document.documentElement;
    const box = parent.getBoundingClientRect();
    const width = box.width || window.innerWidth;
    const height = window.innerHeight - Math.max(0, box.top);
    const wanted = QUERY.get("compact");
    const square = Math.max(width, height) <= WALL_LIMIT && Math.abs(width - height) <= 0.2 * Math.max(width, height);
    const compact = wanted === "1" || (wanted !== "0" && square);
    const changed = compact !== this._compact;
    this._compact = compact;
    this._setAttribute("compact", compact);
    this._setAttribute("narrow", compact || this._narrow);
    // screens differ in pixel density: the design stays 480 wide and the whole of it is scaled
    const zoom = compact ? Math.min(2, Math.max(0.5, Math.min(width, height) / WALL_SIZE)) : 1;
    this.style.zoom = compact ? zoom : "";
    this.style.height = compact ? `${height / zoom}px` : "";
    if (changed && this._ready) this._render();
  }

  // text

  get _lang() {
    const states = this._hass ? this._hass.states : {};
    const wall = this._compact ? states[WALL_LANGUAGE] : null;
    const language = (QUERY.get("lang") || (wall && wall.state) || (this._hass && this._hass.language) || "en").split("-")[0];
    return STRINGS[language] ? language : "en";
  }

  get _t() {
    return STRINGS[this._lang];
  }

  _number(value, decimals = 0) {
    if (value === null || value === undefined) return "—";
    return Number(value).toLocaleString(this._lang, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  _unit(unit) {
    return or(this._t.units[unit], or(unit, ""));
  }

  _reading(name, decimals) {
    const item = this._datapoints[name];
    const value = this._dp[name];
    if (value === null || value === undefined) return "—";
    if (item && item.options) return or(item.options[value], String(value));
    const text = this._number(value, or(decimals, item ? item.decimals : 0));
    const unit = this._unit(item ? item.unit : "");
    return unit ? `${text} ${unit}` : text;
  }

  _problem(err) {
    const texts = this._t.errors;
    const failure = err || {};
    const text = or(texts[failure.code], texts.other);
    return typeof text === "function" ? text(failure.message) : text;
  }

  // start

  async _start() {
    this._started = true;
    this._fit();
    this._render();
    try {
      const info = await this._hass.callWS({ type: `${DOMAIN}/info` });
      this._units = info.units;
      this._admin = info.is_admin;
      if (!this._units.length) {
        this._fatal = this._t.noUnit;
        this._render();
        return;
      }
      const known = this._units.find((unit) => unit.entry_id === this._entry);
      this._entry = (known || this._units[0]).entry_id;
      await this._load();
    } catch (err) {
      this._fatal = err && err.code === "unknown_command" ? this._t.noUnit : this._problem(err);
      this._render();
    }
  }

  async _load() {
    const schema = await this._call("schema", { language: this._lang });
    this._schema = schema;
    this._datapoints = byName(schema.datapoints);
    this._setpoints = byName(schema.setpoints);
    this._loadedLang = this._lang;
    this._unsubscribe = this._hass.connection.subscribeMessage((event) => this._onEvent(event), {
      type: `${DOMAIN}/subscribe`,
      entry_id: this._entry,
    });
    await this._unsubscribe;
  }

  _call(command, fields = {}) {
    return this._hass.callWS({ type: `${DOMAIN}/${command}`, entry_id: this._entry, ...fields });
  }

  _onEvent(event) {
    const first = !this._ready;
    Object.assign(this._dp, event.dp);
    Object.assign(this._sp, event.sp);
    this._status = { available: event.available, virtual: event.virtual, faults: event.faults, words: event.words };
    this._ready = true;
    if (first) this._openTab(this._tab);
    else this._refresh();
  }

  // drawing

  _render() {
    const t = this._t;
    const root = this.shadowRoot;
    if (!root.querySelector("main")) {
      root.innerHTML = `<style>${STYLE}</style>
        <header>
          <button class="menu" data-action="menu" aria-label="Menu">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
          </button>
          <h1 id="title">${esc(t.title)}</h1><span id="units"></span>
          <span class="status" id="status"><i class="dot"></i><span></span></span>
        </header>
        <nav class="tabs" role="tablist"></nav>
        <main></main>
        <dialog id="ask"><div id="ask-text"></div><form method="dialog">
          <button class="btn" value="no">${esc(t.cancel)}</button>
          <button class="btn primary" value="yes">${esc(t.ok)}</button>
        </form></dialog>`;
    }
    const units = root.getElementById("units");
    units.innerHTML =
      this._units && this._units.length > 1
        ? `<select data-unit aria-label="Unit">${this._units
            .map((u) => `<option value="${esc(u.entry_id)}" ${u.entry_id === this._entry ? "selected" : ""}>${esc(u.title)}</option>`)
            .join("")}</select>`
        : "";
    this._drawTabs();
    const main = root.querySelector("main");
    if (this._fatal) main.innerHTML = `<div class="card empty">${esc(this._fatal)}</div>`;
    else if (!this._ready) main.innerHTML = `<div class="card empty">${esc(t.loading)}</div>`;
    else main.innerHTML = this._page();
    if (this._ready) this._refresh();
  }

  _drawTabs() {
    const t = this._t;
    const count = this._status.faults.length;
    this.shadowRoot.querySelector("nav.tabs").innerHTML = TABS.map(
      (tab) => `<button role="tab" aria-selected="${tab === this._tab}" data-action="tab" data-tab="${tab}">
        <svg class="tab-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[tab]}"/></svg>${esc(t.tabs[tab])}${
        tab === "faults" && count ? `<span class="count">${count}</span>` : ""
      }</button>`
    ).join("");
  }

  _page() {
    switch (this._tab) {
      case "settings": return this._settingsPage();
      case "schedule": return this._schedulePage();
      case "data": return this._dataPage();
      case "service": return this._servicePage();
      case "faults": return this._faultsPage();
      default: return this._overviewPage();
    }
  }

  _refresh() {
    const root = this.shadowRoot;
    const { available, faults } = this._status;
    const status = root.getElementById("status");
    status.classList.toggle("bad", !available);
    status.lastElementChild.textContent = available ? this._t.online : this._t.offline;
    const shown = this._shownFaults !== faults.length;
    this._shownFaults = faults.length;
    if (shown) this._drawTabs();
    switch (this._tab) {
      case "overview": this._refreshOverview(shown); break;
      case "faults": if (shown || !root.querySelector(".fault")) this._drawFaults(); this._drawWords(); break;
      case "schedule": this._refreshBanner(); break;
      default: break;
    }
    root.querySelectorAll("[data-dp]").forEach((node) => {
      const item = this._datapoints[node.dataset.dp];
      const value = this._dp[node.dataset.dp];
      if (item && item.flag) node.innerHTML = `<i class="lamp ${value ? "on" : ""}"></i>${esc(value ? this._t.on : this._t.offState)}`;
      else node.textContent = this._reading(node.dataset.dp);
    });
    root.querySelectorAll("[data-name]").forEach((node) => this._fillControl(node));
    root.querySelectorAll("[data-clock]").forEach((node) => (node.textContent = this._deviceClock()));
  }

  _fillControl(node) {
    if (node === this.shadowRoot.activeElement || this._pending[node.dataset.name]) return;
    const value = this._sp[node.dataset.name];
    if (value === null || value === undefined) return;
    if (node.type === "checkbox") node.checked = Boolean(value);
    else if (node.tagName === "SPAN") {
      const item = this._setpoints[node.dataset.name] || {};
      node.textContent = or((item.options || {})[value], this._number(value, item.decimals));
    }
    else if (String(node.value) !== String(value)) node.value = value;
  }

  _deviceClock() {
    const { Date: date, Month, Year, Hour, Min } = this._sp;
    if (Hour === undefined || date === undefined) return "—";
    const two = (n) => String(n).padStart(2, "0");
    return `${two(date)}.${two(Month)}.20${two(Year)}  ${two(Hour)}:${two(Min)}`;
  }

  // overview

  _overviewPage() {
    const t = this._t;
    const modeButton = (mode) => `<button class="btn" data-action="mode" data-mode="${mode}" aria-pressed="false">${esc(t.modes[mode])}</button>`;
    return `<div class="banner" id="faults-banner" hidden><span></span><button class="btn" data-action="tab" data-tab="faults">${esc(t.showFaults)}</button></div>
      <div class="overview">
        <div class="card">
          <div class="scheme" id="scheme">
            <svg viewBox="${this._compact ? "50 34 420 232" : "0 0 520 300"}" aria-hidden="true">
              <rect class="body" x="120" y="44" width="280" height="212" rx="14"/>
              <path class="flow fresh" d="M60 62 H150 L370 238 H460"/>
              <path class="flow stale" d="M460 62 H370 L150 238 H60"/>
              <path class="dash" d="M60 62 H150 L370 238 H460"/>
              <path class="dash" d="M460 62 H370 L150 238 H60"/>
              <g id="fan-supply"><circle class="fan" cx="349" cy="221" r="19"/><path class="blades" d="${this._blades(349, 221)}"/></g>
              <g id="fan-exhaust"><circle class="fan" cx="171" cy="221" r="19"/><path class="blades" d="${this._blades(171, 221)}"/></g>
              <polygon class="core" points="260,88 322,150 260,212 198,150"/>
              <text class="core-text" id="core" x="260" y="152">—</text>
              <text class="core-sub" x="260" y="168">${esc(t.recovery)}</text>
            </svg>
            <div class="port tl"><span>${esc(t.outdoor)}</span><b data-dp="T_Outdoor"></b></div>
            <div class="port tr"><span>${esc(t.extract)}</span><b data-dp="T_Extract"></b></div>
            <div class="port bl"><b data-dp="T_Exhaust"></b><span>${esc(t.exhaust)}</span></div>
            <div class="port br"><b data-dp="T_Supply"></b><span>${esc(t.supply)}</span></div>
          </div>
          <div class="chips" id="chips"></div>
        </div>
        <div class="card control">
          <h2>${esc(t.control)}</h2>
          <div class="modes">
            <button class="btn wide" data-action="auto" aria-pressed="false">${esc(t.scheduleMode)}</button>
            ${[1, 2, 3, 4, 5].map(modeButton).join("")}
            <button class="btn" data-action="mode" data-mode="0" aria-pressed="false">${esc(t.off)}</button>
          </div>
          <p class="now" id="now"></p>
          <div class="target">
            <button class="btn" data-action="target" data-step="-1" aria-label="−">−</button>
            <div><b id="target-value">—</b><span class="muted small" id="target-label"></span></div>
            <button class="btn" data-action="target" data-step="1" aria-label="+">+</button>
          </div>
        </div>
        <div class="tiles span" id="tiles"></div>
      </div>`;
  }

  _blades(cx, cy) {
    let path = "";
    for (let i = 0; i < 4; i += 1) {
      const angle = (i * Math.PI) / 2;
      const point = (r, a) => `${(cx + r * Math.cos(angle + a)).toFixed(1)} ${(cy + r * Math.sin(angle + a)).toFixed(1)}`;
      path += `M${cx} ${cy} Q${point(10, -0.6)} ${point(15, 0)} Q${point(10, 0.5)} ${cx} ${cy}Z`;
    }
    return path;
  }

  _targetName() {
    const side = this._sp.AirTemp_ControlStrategy === 1 ? "Extract" : "Supply";
    const mode = or({ 1: "Unoccupied", 2: "Economy", 3: "Comfort" }[this._dp.CurrentOperatingMode], "Comfort");
    return `AirTemp_${side}Target_${mode}`;
  }

  _refreshOverview(faultsChanged) {
    const t = this._t;
    const root = this.shadowRoot;
    if (!root.getElementById("scheme")) return;
    const { dp, sp } = { dp: this._dp, sp: this._sp };
    const { virtual, faults } = this._status;

    const banner = root.getElementById("faults-banner");
    if (banner && (faultsChanged || banner.hidden === Boolean(faults.length))) {
      banner.hidden = !faults.length;
      banner.style.display = faults.length ? "" : "none";
      banner.firstElementChild.textContent = t.faultsActive(faults.length);
    }

    const running = dp.CurrentOperatingMode !== 0 && dp.CurrentOperatingMode !== undefined;
    const scheme = root.getElementById("scheme");
    scheme.classList.toggle("running", running);
    const spin = (output) => `${Math.max(0.35, 3 - or(output, 0) / 40).toFixed(2)}s`;
    root.getElementById("fan-supply").style.setProperty("--spin", spin(dp.Fan1_Output));
    root.getElementById("fan-exhaust").style.setProperty("--spin", spin(dp.Fan2_Output));
    root.getElementById("core").textContent = virtual.recovery_efficiency === undefined ? "—" : `${this._number(virtual.recovery_efficiency)} %`;

    const auto = sp.ControlMode === 0;
    root.querySelector('[data-action="auto"]').setAttribute("aria-pressed", String(auto));
    root.querySelectorAll('[data-action="mode"]').forEach((button) => {
      button.setAttribute("aria-pressed", String(!auto && Number(button.dataset.mode) === dp.CurrentOperatingMode));
    });
    const how = { 0: t.onSchedule, 1: t.manual, 2: t.temporary }[sp.ControlMode];
    const state = `${or(t.modes[dp.CurrentOperatingMode], "—")}${how ? ` · ${how}` : ""}`;
    root.getElementById("now").textContent = `${t.now}: ${state}`;
    if (this._compact) root.getElementById("title").textContent = state;

    const name = this._targetName();
    const extract = name.includes("Extract");
    if (this._targetDraft === undefined) root.getElementById("target-value").textContent = `${this._number(sp[name], 1)} °C`;
    const suffix = or({ 1: 1, 2: 2 }[dp.CurrentOperatingMode], 3);
    root.getElementById("target-label").textContent = `${extract ? t.targetExtract : t.targetSupply} · ${t.modes[suffix]}`;

    const chips = [];
    if (dp.FreeCooling_ActiveOrNot) chips.push(t.freeCooling);
    if (dp.AirTemp_ERC_Deicing_HeatExchangerActive || dp.AirTemp_ERC_Deicing_FansActive) chips.push(t.deicing);
    if (dp.BoostMode_RemainingTimer_Minutes > 0) chips.push(t.boostLeft(dp.BoostMode_RemainingTimer_Minutes));
    root.getElementById("chips").innerHTML = chips.map((chip) => `<span class="chip">${esc(chip)}</span>`).join("");

    root.getElementById("tiles").innerHTML = this._tiles();
  }

  _tile(title, value, sub = "", extra = "") {
    return `<div class="tile"><span>${esc(title)}</span><b>${esc(value)}</b>${sub ? `<small>${esc(sub)}</small>` : ""}${extra}</div>`;
  }

  _tiles() {
    const t = this._t;
    const { _dp: dp, _sp: sp } = this;
    const fan = (title, flow, output, rpm) =>
      dp[flow]
        ? this._tile(title, this._reading(flow), `${this._reading(output, 0)} · ${this._reading(rpm)}`)
        : this._tile(title, this._reading(output, 0), this._reading(rpm));
    const tiles = [
      fan(t.supplyFan, "Airflow_Supply", "Fan1_Output", "Fan1_RPM"),
      fan(t.exhaustFan, "Airflow_Exhaust", "Fan2_Output", "Fan2_RPM"),
      this._tile(t.phase, this._reading("AirTemp_PhaseControl_WhatPhase"), `${t.presentTarget}: ${this._reading("AirTemp_SupplyControl_PresentSetpoint")}`),
    ];
    if (sp.AirTemp_ERC_TypeInstalled === 1) tiles.push(this._tile(t.bypass, this._reading("AirTemp_ERC_Passive_BypassPosition", 0)));
    else tiles.push(this._tile(t.rotor, this._reading("AirTemp_ERC_Rotary_Speed", 0)));

    const inputs = [sp.AI1_Configuration, sp.AI2_Configuration, sp.AI3_Configuration];
    if (inputs.includes(1)) tiles.push(this._tile(t.humidity, this._reading("AI_ExtractAirHumidity")));
    if (inputs.includes(3)) tiles.push(this._tile(`${t.humidity}, ${t.supply.toLowerCase()}`, this._reading("AI_SupplyAirHumidity")));
    if (inputs.includes(2)) tiles.push(this._tile(t.co2, this._reading("AI_ExtractAirCO2")));

    const left = dp.Filter_RemainingDays;
    const period = sp.Filter_TimerPeriod_Days;
    const share = period ? Math.min(100, Math.max(0, (left / period) * 100)) : 0;
    const bar = `<div class="bar"><i style="width:${share.toFixed(0)}%${share < 10 ? ";background:var(--nest-warning)" : ""}"></i></div>
      <button class="btn" data-action="press" data-press="Filter_Reset" data-ask="filterResetAsk">${esc(t.filterReset)}</button>`;
    tiles.push(this._tile(t.filter, left === undefined ? "—" : `${this._number(left)} ${this._unit("d")}`, t.filterLeft, bar));
    if (this._status.virtual.running_hours !== undefined) {
      tiles.push(this._tile(t.hours, `${this._number(this._status.virtual.running_hours)} ${this._unit("h")}`));
    }
    return tiles.join("");
  }

  // register lists

  _control(item, editable) {
    const name = esc(item.name);
    const off = editable ? "" : "disabled";
    if (item.read_only) return `<span class="value" data-name="${name}"></span>`;
    switch (item.kind) {
      case "button":
        return `<button class="btn ${item.danger ? "danger" : ""}" data-action="press" data-press="${name}" ${off}>${esc(this._t.run)}</button>`;
      case "switch":
        return `<label class="toggle"><input type="checkbox" data-name="${name}" ${off} aria-label="${esc(item.label)}"><i></i></label>`;
      case "select":
        return `<select data-name="${name}" ${off} aria-label="${esc(item.label)}">${Object.entries(item.options || {})
          .map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`)
          .join("")}</select>`;
      default: {
        const step = item.decimals ? 10 ** -item.decimals : 1;
        const stepper = (direction, sign) =>
          `<button class="btn stepper" data-action="step" data-for="${name}" data-direction="${direction}" ${off} aria-label="${sign}">${sign}</button>`;
        return `${stepper(-1, "−")}<input type="number" inputmode="decimal" data-name="${name}" min="${item.min}" max="${item.max}" step="${step}" ${off} aria-label="${esc(item.label)}">${stepper(1, "+")}
          <span class="unit">${esc(this._unit(item.unit))}</span>`;
      }
    }
  }

  _settingRow(item, service) {
    const t = this._t;
    const editable = service ? Boolean(this._token) : item.level === "user" || this._admin;
    const meta = [];
    if (service) {
      meta.push(`#${item.address}`);
      if (item.kind === "number" || item.kind === "select") {
        const fallback = or((item.options || {})[item.default], this._number(item.default, item.decimals));
        meta.push(`${t.factory}: ${fallback}`);
      }
    } else if (!editable) meta.push(t.adminOnly);
    return `<div class="row" data-row="${esc(item.name)}" title="${esc(item.hint)}">
      <div class="row-text"><div>${esc(item.label)}</div>${meta.length ? `<div class="row-meta">${esc(meta.join(" · "))}</div>` : ""}</div>
      <div class="row-control">${this._control(item, editable)}<span class="row-state"></span></div>
    </div>`;
  }

  _sectionsOf(items, order) {
    const grouped = {};
    items.forEach((item) => {
      grouped[item.section] = grouped[item.section] || [];
      grouped[item.section].push(item);
    });
    const known = order.filter((section) => grouped[section]);
    return { grouped, sections: [...known, ...Object.keys(grouped).filter((section) => !known.includes(section))] };
  }

  _browser(key, items, order, drawRow, extras = {}) {
    const { grouped, sections } = this._sectionsOf(items, order);
    const all = [...Object.keys(extras).filter((section) => !sections.includes(section)), ...sections];
    if (!all.includes(this._section[key])) this._section[key] = all[0];
    this._browserState = { key, grouped, extras, drawRow, items };
    const titles = this._t.sections;
    return `<input type="search" class="finder" data-find placeholder="${esc(this._t.search)}" value="${esc(this._find)}">
      <div class="browser">
        <div class="sections">${all
          .map(
            (section) => `<button data-action="section" data-section="${section}" aria-current="${section === this._section[key]}">
              ${esc(or(titles[section], section))}${grouped[section] ? `<span>${grouped[section].length}</span>` : ""}</button>`
          )
          .join("")}</div>
        <div class="card rows" id="rows">${this._rows()}</div>
      </div>`;
  }

  _rows() {
    const { key, grouped, extras, drawRow, items } = this._browserState;
    const find = this._find.trim().toLowerCase();
    if (find) {
      const found = items.filter((item) => item.label.toLowerCase().includes(find) || item.name.toLowerCase().includes(find));
      return found.length ? found.map(drawRow).join("") : `<div class="empty">${esc(this._t.nothingFound)}</div>`;
    }
    const section = this._section[key];
    return `${extras[section] ? extras[section]() : ""}${(grouped[section] || []).map(drawRow).join("")}`;
  }

  _settingsPage() {
    const items = this._schema.setpoints.filter(
      (item) => item.level !== "service" && item.section !== "schedule" && !item.danger && !item.read_only
    );
    const order = ["operation", "temperature", "air_quality", "free_cooling", "fans", "temporary", "cooker_hood", "time", "system"];
    return this._browser("settings", items, order, (item) => this._settingRow(item, false), {
      time: () => this._clockRow(),
    });
  }

  _clockRow() {
    const t = this._t;
    return `<div class="row"><div class="row-text"><div>${esc(t.clock)}</div><div class="row-meta" data-clock></div></div>
      <div class="row-control"><button class="btn" data-action="sync">${esc(t.syncClock)}</button></div></div>`;
  }

  _dataPage() {
    const order = ["temperature", "air", "fans", "operation", "coils", "dampers", "inputs", "temporary", "schedule", "system", "device"];
    return this._browser("data", this._schema.datapoints, order, (item) => `<div class="row" title="${esc(item.hint)}">
      <div class="row-text">${esc(item.label)}</div><div class="value" data-dp="${esc(item.name)}"></div></div>`);
  }

  // schedule

  _schedulePage() {
    const t = this._t;
    const scheduler = this._setpoints.Scheduler_Mode;
    return `<div class="banner info" id="schedule-banner" hidden><span>${esc(t.scheduleOff)}</span>
        <button class="btn" data-action="auto">${esc(t.scheduleOn)}</button></div>
      <div class="card"><h2>${esc(t.week)}</h2><div id="week"><div class="empty">${esc(t.loading)}</div></div></div>
      <div class="card" id="day"></div>
      ${scheduler ? `<div class="card rows">${this._settingRow(scheduler, false)}</div>` : ""}`;
  }

  async _openSchedule() {
    try {
      const result = await this._call("schedule");
      this._days = result.days;
      this._draft = this._activeEvents(this._day);
      this._drawSchedule();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _activeEvents(day) {
    return this._days[day].filter((event) => event[2] > 0).map((event) => [...event]);
  }

  _segments(day) {
    const minutes = (event) => event[0] * 60 + event[1];
    const events = this._activeEvents(day).sort((a, b) => minutes(a) - minutes(b));
    let before;
    for (let back = 1; back < DAYS_IN_WEEK && !before; back += 1) {
      before = this._activeEvents((day + DAYS_IN_WEEK - back) % DAYS_IN_WEEK).sort((a, b) => minutes(a) - minutes(b)).pop();
    }
    const parts = [];
    if (before && (!events.length || minutes(events[0]) > 0)) parts.push({ from: 0, to: events.length ? minutes(events[0]) : 1440, mode: before[2] });
    events.forEach((event, index) => {
      parts.push({ from: minutes(event), to: index + 1 < events.length ? minutes(events[index + 1]) : 1440, mode: event[2] });
    });
    return parts;
  }

  _drawSchedule() {
    const t = this._t;
    const root = this.shadowRoot;
    const week = root.getElementById("week");
    if (!week || !this._days) return;
    const rows = t.dayShort.map((name, day) => {
      const parts = this._segments(day)
        .map((part) => `<i class="m${part.mode}" style="left:${(part.from / 14.4).toFixed(2)}%;width:${((part.to - part.from) / 14.4).toFixed(2)}%"></i>`)
        .join("");
      return `<button data-action="day" data-day="${day}" aria-current="${day === this._day}"><span>${esc(name)}</span><div class="line">${parts}</div></button>`;
    });
    const legend = [1, 2, 3, 4, 5].map((mode) => `<span><i class="m${mode}"></i>${esc(t.scheduleModes[mode])}</span>`).join("");
    week.innerHTML = `<div class="week">${rows.join("")}</div>
      <div class="hours"><span></span><div><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div></div>
      <div class="legend">${legend}</div>`;
    this._drawDay();
  }

  _drawDay() {
    const t = this._t;
    const day = this.shadowRoot.getElementById("day");
    if (!day || !this._draft) return;
    const two = (n) => String(n).padStart(2, "0");
    const options = (selected) =>
      [1, 2, 3, 4, 5].map((mode) => `<option value="${mode}" ${mode === selected ? "selected" : ""}>${esc(t.scheduleModes[mode])}</option>`).join("");
    const events = this._draft
      .map(
        (event, index) => `<div class="event">
          <input type="time" data-event="${index}" data-field="time" value="${two(event[0])}:${two(event[1])}" aria-label="${esc(t.startsAt)}">
          <select data-event="${index}" data-field="mode" aria-label="${esc(t.mode)}">${options(event[2])}</select>
          <input type="number" min="0" max="30" step="1" data-event="${index}" data-field="temp" value="${event[3]}" aria-label="${esc(t.temperature)}">
          <button class="btn" data-action="remove-event" data-index="${index}" aria-label="${esc(t.removeEvent)}">✕</button>
        </div>`
      )
      .join("");
    const head = this._draft.length
      ? `<div class="event event-head"><span>${esc(t.startsAt)}</span><span>${esc(t.mode)}</span><span>°C</span><span></span></div>`
      : `<div class="empty">${esc(t.noEvents)}</div>`;
    const dirty = JSON.stringify(this._draft) !== JSON.stringify(this._activeEvents(this._day));
    const days = t.dayShort
      .map((name, index) => (index === this._day ? "" : `<label><input type="checkbox" data-copy="${index}">${esc(name)}</label>`))
      .join("");
    day.innerHTML = `<h2>${esc(t.dayNames[this._day])}</h2>${head}${events}
      <div class="actions">
        <button class="btn" data-action="add-event" ${this._draft.length >= EVENTS_IN_DAY ? "disabled" : ""}>${esc(t.addEvent)}</button>
        <span class="grow"></span>
        <button class="btn" data-action="revert-day" ${dirty ? "" : "disabled"}>${esc(t.revert)}</button>
        <button class="btn primary" data-action="save-day" ${dirty ? "" : "disabled"}>${esc(t.save)}</button>
      </div>
      <div class="actions"><span class="muted">${esc(t.copyTo)}</span><div class="days">${days}</div>
        <button class="btn" data-action="copy-day" ${dirty ? "disabled" : ""}>${esc(t.copy)}</button></div>`;
  }

  async _saveDay() {
    const minutes = (event) => event[0] * 60 + event[1];
    const events = [...this._draft].sort((a, b) => minutes(a) - minutes(b));
    while (events.length < EVENTS_IN_DAY) events.push([0, 0, 0, 0]);
    try {
      const result = await this._call("schedule_write", { day: this._day, events });
      this._days = result.days;
      this._draft = this._activeEvents(this._day);
      this._drawSchedule();
      this._toast(this._t.saved);
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  async _copyDay() {
    const targets = [...this.shadowRoot.querySelectorAll("[data-copy]:checked")].map((box) => Number(box.dataset.copy));
    if (!targets.length) return;
    try {
      const result = await this._call("schedule_copy", { source: this._day, targets });
      this._days = result.days;
      this._drawSchedule();
      this._toast(this._t.saved);
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _refreshBanner() {
    const banner = this.shadowRoot.getElementById("schedule-banner");
    if (!banner) return;
    const show = this._sp.ControlMode !== 0;
    banner.hidden = !show;
    banner.style.display = show ? "" : "none";
  }

  // service

  _servicePage() {
    const t = this._t;
    if (!this._admin) return `<div class="card empty">${esc(t.needAdmin)}</div>`;
    if (!this._token) {
      return `<div class="card lockbox"><h2>${esc(t.locked)}</h2><p class="muted">${esc(t.lockedText)}</p>
        <form data-form="unlock"><input type="password" inputmode="numeric" autocomplete="off" name="pin" aria-label="${esc(t.pin)}" placeholder="${esc(t.pin)}" required>
        <button class="btn primary">${esc(t.unlock)}</button></form></div>${this._connectionCard()}`;
    }
    const items = this._schema.setpoints.filter((item) => item.level === "service");
    const order = ["maintenance", "operation", "fans", "fan_hw", "temperature", "temp_sensors", "pressure", "analog_inputs", "digital_inputs", "dampers", "fire", "coils", "recovery", "air_quality", "system", "network", "fieldbus"];
    return `<div class="banner info"><span id="unlocked"></span><button class="btn" data-action="lock">${esc(t.lock)}</button></div>
      ${this._browser("service", items, order, (item) => this._settingRow(item, true), { connection: () => this._connectionCard(true) })}`;
  }

  _connectionCard(bare) {
    const t = this._t;
    const unit = (this._units || []).find((candidate) => candidate.entry_id === this._entry) || {};
    const facts = [
      [t.host, unit.host], [t.port, unit.port], [t.unitId, unit.unit], [t.framing, unit.framing === "rtu" ? "RTU over TCP" : "Modbus TCP"],
      [t.ip, this._status.virtual.ip], [t.mac, this._status.virtual.mac], [t.firmware, unit.firmware], [t.bootloader, unit.bootloader],
      [t.eeprom, this._dp.WriteToEepromCounter],
    ];
    const body = `<div class="facts">${facts.map(([name, value]) => `<div><span>${esc(name)}</span>${esc(or(value, "—"))}</div>`).join("")}</div>`;
    return bare ? `<div style="padding:12px 0">${body}</div>` : `<div class="card"><h2>${esc(t.connection)}</h2>${body}</div>`;
  }

  _tick() {
    if (!this._token) return;
    const left = Math.round(this._tokenUntil - Date.now() / 1000);
    if (left <= 0) {
      this._lock();
      return;
    }
    const label = this.shadowRoot.getElementById("unlocked");
    if (label) label.textContent = this._t.unlockedFor(`${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`);
  }

  _lock() {
    this._token = null;
    if (this._tab === "service") this._render();
  }

  // faults

  _faultsPage() {
    const t = this._t;
    return `<div class="card"><h2>${esc(t.activeFaults)}</h2><div id="active"></div>
        <div class="actions"><button class="btn" data-action="press" data-press="ResetErrors">${esc(t.resetErrors)}</button></div></div>
      <div class="card"><div class="actions" style="margin:0 0 8px"><h2 class="grow" style="margin:0">${esc(t.history)}</h2>
        ${this._admin ? `<button class="btn" data-action="clear-log">${esc(t.clearHistory)}</button>` : ""}</div>
        <div id="log"><div class="empty">${esc(t.loading)}</div></div></div>
      <div class="card"><h2>${esc(t.rawWords)}</h2><div class="words" id="words"></div></div>`;
  }

  _faultName(fault) {
    const name = fault.name;
    if (name && this._schema.faults[name]) return this._schema.faults[name];
    if (fault.word !== undefined) return this._t.unnamedBit(fault.word, fault.bit);
    const raw = (fault.id || "").split(":").pop();
    return raw.includes(".") ? this._t.unnamedBit(...raw.split(".")) : raw;
  }

  _drawFaults() {
    const t = this._t;
    const active = this.shadowRoot.getElementById("active");
    if (!active) return;
    const { faults } = this._status;
    active.innerHTML = faults.length
      ? faults.map((fault) => `<div class="fault"><span class="kind ${esc(fault.kind)}">${esc(t.kinds[fault.kind])}</span><span>${esc(this._faultName(fault))}</span></div>`).join("")
      : `<div class="empty">${esc(t.noFaults)}</div>`;
    this._loadLog();
  }

  async _loadLog() {
    const t = this._t;
    try {
      const { log } = await this._call("log");
      const box = this.shadowRoot.getElementById("log");
      if (!box) return;
      const when = new Intl.DateTimeFormat(this._lang, { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
      box.innerHTML = log.length
        ? log.map((item) => `<div class="fault">
            <span class="kind ${item.on ? esc(item.kind) : "gone"}">${esc(item.on ? t.appeared : t.cleared)}</span>
            <span>${esc(this._faultName(item))}</span>
            <span class="muted small">${esc(when.format(new Date(item.at)))}</span></div>`).join("")
        : `<div class="empty">${esc(t.noHistory)}</div>`;
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _drawWords() {
    const box = this.shadowRoot.getElementById("words");
    if (!box) return;
    box.innerHTML = Object.entries(this._status.words)
      .map(([name, value]) => `<span>${esc(name)}: ${value === null || value === undefined ? "—" : `0x${value.toString(16).toUpperCase().padStart(4, "0")}`}</span>`)
      .join("");
  }

  // actions

  _onClick(event) {
    const node = event.target.closest("[data-action]");
    if (!node || node.disabled) return;
    const { action } = node.dataset;
    switch (action) {
      case "menu":
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
        break;
      case "tab":
        this._openTab(node.dataset.tab);
        break;
      case "section":
        this._section[this._browserState.key] = node.dataset.section;
        this._find = "";
        this._render();
        break;
      case "mode":
        this._run(this._call("control", { action: "set_mode", mode: Number(node.dataset.mode) }));
        break;
      case "auto":
        this._run(this._call("control", { action: "set_auto" }));
        break;
      case "sync":
        this._run(this._call("control", { action: "sync_clock" }), true);
        break;
      case "target":
        this._nudgeTarget(Number(node.dataset.step));
        break;
      case "step":
        this._stepSetting(node.dataset.for, Number(node.dataset.direction));
        break;
      case "press":
        this._press(node.dataset.press, node.dataset.ask);
        break;
      case "lock":
        this._lock();
        break;
      case "day":
        this._day = Number(node.dataset.day);
        this._draft = this._activeEvents(this._day);
        this._drawSchedule();
        break;
      case "add-event":
        this._draft.push(this._draft.length ? [...this._draft[this._draft.length - 1]] : [8, 0, 4, 20]);
        this._drawDay();
        break;
      case "remove-event":
        this._draft.splice(Number(node.dataset.index), 1);
        this._drawDay();
        break;
      case "revert-day":
        this._draft = this._activeEvents(this._day);
        this._drawDay();
        break;
      case "save-day":
        this._saveDay();
        break;
      case "copy-day":
        this._copyDay();
        break;
      case "clear-log":
        this._clearLog();
        break;
      default:
        break;
    }
  }

  _openTab(tab) {
    this._tab = tab;
    this._find = "";
    history.replaceState(history.state, "", `#${tab}`);
    this._render();
    if (tab === "schedule" && this._ready) this._openSchedule();
    if (tab === "faults" && this._ready) this._drawFaults();
  }

  async _run(promise, confirmSaved) {
    try {
      await promise;
      if (confirmSaved) this._toast(this._t.saved);
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _nudgeTarget(direction) {
    const name = this._targetName();
    const item = this._setpoints[name];
    const start = this._targetDraft && this._targetDraft.name === name ? this._targetDraft.value : this._sp[name];
    if (start === undefined || start === null) return;
    const low = Math.max(item.min, or(this._sp.AirTemp_MinAllowedSetpoint, item.min));
    const high = Math.min(item.max, or(this._sp.AirTemp_MaxAllowedSetpoint, item.max));
    const value = Math.min(high, Math.max(low, start + direction * TARGET_STEP));
    this._targetDraft = { name, value };
    this.shadowRoot.getElementById("target-value").textContent = `${this._number(value, 1)} °C`;
    clearTimeout(this._targetTimer);
    // the value is kept in EEPROM: one write when the tapping stops, not one per tap
    this._targetTimer = setTimeout(async () => {
      const draft = this._targetDraft;
      try {
        const result = await this._call("write", { name: draft.name, value: draft.value });
        this._sp[draft.name] = result.value;
      } catch (err) {
        this._toast(this._problem(err));
      }
      this._targetDraft = undefined;
      this._refresh();
    }, SAVE_PAUSE);
  }

  _stepSetting(name, direction) {
    const item = this._setpoints[name];
    const input = this.shadowRoot.querySelector(`input[data-name="${name}"]`);
    const step = item.unit === "°C" ? TARGET_STEP : item.decimals ? 10 ** -item.decimals : 1;
    const value = Math.min(item.max, Math.max(item.min, (Number(input.value) || 0) + direction * step));
    input.value = value.toFixed(item.decimals);
    this._pending[name] = true;
    clearTimeout(this._stepTimers[name]);
    // as with the target: one write when the tapping stops
    this._stepTimers[name] = setTimeout(() => {
      delete this._pending[name];
      this._commit(input);
    }, SAVE_PAUSE);
  }

  async _press(name, ask) {
    const item = this._setpoints[name] || {};
    const question = ask ? this._t[ask] : item.danger ? `${item.label}. ${this._t.dangerPress}` : null;
    if (question && !(await this._ask(question))) return;
    const fields = { name };
    if (item.level === "service") fields.token = this._token;
    if (item.danger) fields.confirm = true;
    await this._run(this._call("write", fields).catch((err) => this._denied(err)), true);
  }

  _denied(err) {
    if (err && err.code === "service_locked") this._lock();
    throw err;
  }

  async _clearLog() {
    if (!(await this._ask(this._t.clearHistoryAsk))) return;
    await this._run(this._call("log_clear"));
    this._loadLog();
  }

  _ask(text) {
    const dialog = this.shadowRoot.getElementById("ask");
    this.shadowRoot.getElementById("ask-text").textContent = text;
    dialog.returnValue = "no";
    dialog.showModal();
    return new Promise((resolve) => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue === "yes"), { once: true });
    });
  }

  _toast(text) {
    const shown = this.shadowRoot.querySelector(".toast");
    if (shown) shown.remove();
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");
    toast.textContent = text;
    this.shadowRoot.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  _onChange(event) {
    const node = event.target;
    if (node.matches("[data-unit]")) {
      this._switchUnit(node.value);
    } else if (node.matches("[data-name]")) {
      this._commit(node);
    } else if (node.matches("[data-event]")) {
      const entry = this._draft[Number(node.dataset.event)];
      if (node.dataset.field === "time") [entry[0], entry[1]] = node.value.split(":").map(Number);
      if (node.dataset.field === "mode") entry[2] = Number(node.value);
      if (node.dataset.field === "temp") entry[3] = Math.min(30, Math.max(0, Math.round(Number(node.value) || 0)));
      this._drawDay();
    }
  }

  async _commit(node) {
    const name = node.dataset.name;
    const item = this._setpoints[name];
    const value = node.type === "checkbox" ? (node.checked ? 1 : 0) : Number(node.value);
    const row = node.closest(".row");
    const state = row && row.querySelector(".row-state");
    const previous = this._sp[name];
    const mark = (text, kind) => {
      if (!state) return;
      state.textContent = text;
      state.className = `row-state ${kind}`;
    };
    if (item.danger && !(await this._ask(`${item.label}: ${node.type === "checkbox" ? (value ? this._t.on : this._t.offState) : value}. ${this._t.dangerAsk}`))) {
      this._fillControl(node);
      return;
    }
    const fields = { name, value };
    if (item.level === "service") fields.token = this._token;
    if (item.danger) fields.confirm = true;
    mark("…", "");
    try {
      const result = await this._call("write", fields);
      this._sp[name] = result.value;
      mark("✓", "ok");
      setTimeout(() => mark("", ""), 2000);
    } catch (err) {
      mark("!", "bad");
      this._sp[name] = previous;
      node.blur();
      this._fillControl(node);
      this._toast(this._problem(err));
      if (err && err.code === "service_locked") this._lock();
    }
  }

  async _switchUnit(entry) {
    this._leave();
    this._entry = entry;
    this._ready = false;
    this._token = null;
    this._dp = {};
    this._sp = {};
    this._render();
    await this._run(this._load());
  }

  _onInput(event) {
    if (!event.target.matches("[data-find]")) return;
    this._find = event.target.value;
    const rows = this.shadowRoot.getElementById("rows");
    rows.innerHTML = this._rows();
    this._refresh();
  }

  async _onSubmit(event) {
    const form = event.target;
    if (form.dataset.form !== "unlock") return;
    event.preventDefault();
    const pin = form.elements.pin.value;
    form.elements.pin.value = "";
    try {
      const result = await this._call("unlock", { pin });
      this._token = result.token;
      this._tokenUntil = Date.now() / 1000 + result.seconds;
      this._render();
      this._tick();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }
}

if (!customElements.get("alpicair-nest-panel")) customElements.define("alpicair-nest-panel", AlpicAirNestPanel);
