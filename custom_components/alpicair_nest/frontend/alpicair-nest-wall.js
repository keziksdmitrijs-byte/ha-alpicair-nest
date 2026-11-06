/* AlpicAir NEST on a square wall panel such as the SONOFF NSPanel Pro.
 *
 * A panel of its own, drawn for 480 x 480 and fingers: a home screen, a menu, submenus, and full
 * screen editors, so no on-screen keyboard is ever needed. Everything the unit offers is reachable.
 *
 * Wall panels run old browsers (Android 8.1 with a WebView that can be Chromium 61) on slow chips.
 * So: ES2018 only, no ?. or ??, no gap on flex, no inset, clamp, color-mix or backdrop-filter, and
 * short transform animations only. tests/check_panels.js enforces this and the menu's coverage.
 *
 * Another card can host it: set `embed` before `hass`, to { theme, accent, language, leave, unit }.
 * Embedded, it fills its host instead of scaling itself, takes its look from the host, and leaving it
 * fires `alpicair-nest-leave` instead of navigating. `home()` brings it back to the home screen.
 */

const DOMAIN = "alpicair_nest";
const QUERY = new URLSearchParams(location.search);
const BASE = 480;
const IDLE_MS = 120000;
const SAVE_PAUSE = 800;
const TARGET_STEP = 0.5;
// one tap on the home screen, by Fans_ControlStrategy: %, m³/h, Pa
const FAN_STEPS = { 0: 5, 1: 10, 2: 5 };
const DAYS = 7;
const EVENTS = 10;
const MENU_MAX = 1.7;

const ACCENTS = {
  blue: "#3b82f6", teal: "#14b8a6", green: "#22c55e", amber: "#f59e0b",
  orange: "#f97316", red: "#ef4444", pink: "#ec4899", purple: "#8b5cf6",
};
const THEMES = ["auto", "light", "dark"];
// the home screen: the house with its air flows, or the big fan ring
const LAYOUTS = ["house", "fan"];
const LANGUAGES = { lv: "Latviešu", ru: "Русский", en: "English" };
const THEME_ENTITY = "input_select.nspanel_theme";
const ACCENT_ENTITY = "input_select.nspanel_accent";
const LANGUAGE_ENTITY = "input_select.nspanel_language";
const HOME_ENTITY = "input_text.nspanel_home";
const NOT_TARGETS = ["alpicair-nest-wall", "config", "developer-tools", "notfound", "profile"];

const ICONS = {
  back: "M15 5l-7 7 7 7",
  chevron: "M9 5l7 7-7 7",
  home: "M4 11l8-7 8 7v9h-5v-6H9v6H4z",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  power: "M12 3v9M6.3 6.3a8 8 0 1 0 11.4 0",
  thermo: "M12 3a2 2 0 0 0-2 2v9.3a4 4 0 1 0 4 0V5a2 2 0 0 0-2-2z",
  fan: "M12 12c0-4 1-8 4-8s3 4 0 6zM12 12c4 0 8 1 8 4s-4 3-6 0zM12 12c0 4-1 8-4 8s-3-4 0-6zM12 12c-4 0-8-1-8-4s4-3 6 0z",
  leaf: "M5 19C5 10 11 4 20 4c0 9-6 15-15 15zM5 19l7-7",
  drop: "M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z",
  calendar: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4",
  chart: "M5 20V11M12 20V4M19 20v-7",
  alert: "M12 4l9 16H3zM12 10v5M12 17.5v.5",
  sliders: "M3 7h11M18 7h3M3 17h3M10 17h11M16 5v4M8 15v4",
  lock: "M7 11V8a5 5 0 0 1 10 0v3M5 11h14v9H5z",
  sun: "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5",
  snow: "M12 3v18M4 7.5l16 9M20 7.5l-16 9M9 4.5l3 3 3-3M9 19.5l3-3 3 3",
  clock: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 7v5l3 2",
  filter: "M3 5h18l-7 8v6l-4 2v-8z",
  bolt: "M13 3L5 14h6l-1 7 8-11h-6z",
  moon: "M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z",
  person: "M12 4a4 4 0 1 0 0 8a4 4 0 1 0 0-8zM4 21c0-5 4-7 8-7s8 2 8 7",
  rocket: "M5 12l7-8 7 8M5 19l7-8 7 8",
  hood: "M4 18h16L15 9V4H9v5z",
  wifi: "M12 20h.01M8.5 16a5 5 0 0 1 7 0M5 12.5a10 10 0 0 1 14 0M2 9a14 14 0 0 1 20 0",
  info: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 11v5M12 8v.5",
  palette: "M12 3a9 9 0 1 0 0 18c2 0 2-1.5 1.5-3s.5-2 2-2H18a3 3 0 0 0 3-3c0-6-5-10-9-10z",
  trash: "M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13",
  copy: "M8 8h12v12H8zM4 16V4h12",
  check: "M4 12l5 5 11-11",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  erase: "M9 5h11v14H9l-6-7zM12 9l5 6M17 9l-5 6",
  exit: "M14 4h6v16h-6M4 12h11M10 7l-6 5 6 5",
  list: "M4 6h16M4 12h16M4 18h16",
  flow: "M4 7h6l4 10h6M4 17h6l4-10h6",
  chip: "M7 7h10v10H7zM4 10h3M4 14h3M17 10h3M17 14h3M10 4v3M14 4v3M10 17v3M14 17v3",
  shield: "M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z",
  gauge: "M4 18a9 9 0 1 1 16 0M12 15l4-5",
};

const STRINGS = {
  ru: {
    locale: "ru-RU",
    modes: ["Выключено", "Никого нет", "Эконом", "Комфорт", "Буст", "Вытяжка"],
    scheduleModes: ["Не используется", "Ожидание", "Никого нет", "Эконом", "Комфорт", "Буст"],
    onSchedule: "по расписанию", manual: "вручную", temporary: "временно",
    scheduleMode: "По расписанию", turnOff: "Выключить", mode: "Режим", menu: "Меню",
    outdoor: "С улицы", supply: "Приток", extract: "Вытяжка", exhaust: "Выброс",
    toRooms: "В помещения", fromRooms: "Из помещений", fan: "Вентиляторы", air: "Воздух", humidity: "Влажность",
    recovery: "Рекуперация", filter: "Фильтр", target: "цель", now: "сейчас", phases: ["нагрев", "рекуперация", "охлаждение"],
    offline: "Нет связи с установкой", loading: "Загрузка…", noUnit: "Установка не подключена",
    on: "Вкл", off: "Выкл", run: "Выполнить", ok: "Готово", cancel: "Отмена", confirm: "Продолжить", save: "Сохранить",
    saved: "Сохранено", adminOnly: "Менять могут только администраторы", range: (a, b) => `от ${a} до ${b}`, factory: "заводское",
    dangerSet: "Неверное значение может остановить установку или оборвать связь с ней.",
    dangerRun: "Команда выполнится сразу и может остановить установку.",
    filterAsk: "Сбросить таймер фильтра? Делайте это после замены фильтра.",
    settings: (n) => `Настроек: ${n}`, sections: (n) => `Разделов: ${n}`,
    week: "Неделя", days: ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"],
    daysShort: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    notRunning: "Сейчас ручной режим, расписание не работает", turnOn: "Включить",
    noEvents: "В этот день событий нет", addEvent: "Добавить событие", event: "Событие", time: "Время", temperature: "Температура",
    remove: "Удалить", copyDay: "Скопировать день", copyTo: "Копировать на", copy: "Скопировать", unsaved: "Есть несохранённые изменения",
    schedulerMode: "Как работает расписание", leave: "Выйти без сохранения?", hours: "ч", minutes: "мин",
    pin: "Сервисный PIN", pinHint: "Сверяется с установкой и нигде не сохраняется", pinWrong: "Неверный PIN", lock: "Закрыть сервис",
    open: (t) => `Открыто ещё ${t}`, needAdmin: "Сервис доступен только администраторам",
    active: "Сейчас", history: "История", words: "Слова состояния", noFaults: "Неисправностей нет", noHistory: "История пуста",
    resetErrors: "Сбросить ошибки", clearHistory: "Очистить историю", clearAsk: "Очистить историю? Она хранится только в Home Assistant.",
    appeared: "появилась", cleared: "прошла", kinds: { error: "Ошибка", warning: "Предупреждение", alarm: "Тревога" },
    bit: (w, b) => `${w}, бит ${b}`, flow: "Схема потоков", clock: "Часы установки", syncClock: "Поставить время Home Assistant",
    theme: "Тема", themes: { auto: "Авто", light: "Светлая", dark: "Тёмная" }, accent: "Акцент", language: "Язык",
    host: "Адрес", port: "Порт", unitId: "Адрес Modbus", protocol: "Протокол", mac: "MAC", ip: "IP установки",
    firmware: "Прошивка", bootloader: "Загрузчик", eeprom: "Записей в EEPROM", runningHours: "Моточасы", exit: "Выйти из панели",
    menuButton: "Кнопка в меню", leadsTo: "Куда она ведёт",
    homeLayout: "Главный экран", layouts: { house: "Дом", fan: "Вентилятор" }, fanSpeed: "Скорость вентиляторов",
    closesOnPick: "закроется после выбора", tapOutside: "коснитесь снаружи, чтобы закрыть",
    errors: {
      forbidden: "Для этого нужны права администратора", service_locked: "Сервис закрыт, введите PIN ещё раз",
      wrong_pin: "Неверный PIN", too_many_tries: (s) => `Слишком много попыток, подождите ${s} с`,
      unit_error: "Установка не ответила", invalid_value: "Недопустимое значение", other: "Не получилось",
    },
    units: { rpm: "об/мин", "m³/h": "м³/ч", d: "дн.", h: "ч", min: "мин", s: "с", Pa: "Па", V: "В", mA: "мА" },
  },
  lv: {
    locale: "lv-LV",
    modes: ["Izslēgts", "Neviena nav", "Ekonomija", "Komforts", "Boost", "Nosūcējs"],
    scheduleModes: ["Nav izmantots", "Gaidstāve", "Neviena nav", "Ekonomija", "Komforts", "Boost"],
    onSchedule: "pēc grafika", manual: "manuāli", temporary: "pagaidu",
    scheduleMode: "Pēc grafika", turnOff: "Izslēgt", mode: "Režīms", menu: "Izvēlne",
    outdoor: "No ārpuses", supply: "Pieplūde", extract: "Nosūce", exhaust: "Izmešana",
    toRooms: "Uz telpām", fromRooms: "No telpām", fan: "Ventilatori", air: "Gaiss", humidity: "Mitrums",
    recovery: "Atguve", filter: "Filtrs", target: "mērķis", now: "tagad", phases: ["apsilde", "atguve", "dzesēšana"],
    offline: "Iekārta neatbild", loading: "Ielādē…", noUnit: "Iekārta nav pievienota",
    on: "Iesl.", off: "Izsl.", run: "Izpildīt", ok: "Gatavs", cancel: "Atcelt", confirm: "Turpināt", save: "Saglabāt",
    saved: "Saglabāts", adminOnly: "Mainīt var tikai administratori", range: (a, b) => `no ${a} līdz ${b}`, factory: "rūpnīcas",
    dangerSet: "Nepareiza vērtība var apturēt iekārtu vai pārtraukt savienojumu ar to.",
    dangerRun: "Komanda izpildīsies uzreiz un var apturēt iekārtu.",
    filterAsk: "Atiestatīt filtra taimeri? Dariet to pēc filtra nomaiņas.",
    settings: (n) => `Iestatījumi: ${n}`, sections: (n) => `Sadaļas: ${n}`,
    week: "Nedēļa", days: ["Pirmdiena", "Otrdiena", "Trešdiena", "Ceturtdiena", "Piektdiena", "Sestdiena", "Svētdiena"],
    daysShort: ["Pr", "Ot", "Tr", "Ce", "Pk", "Se", "Sv"],
    notRunning: "Tagad manuāls režīms, grafiks nedarbojas", turnOn: "Ieslēgt",
    noEvents: "Šajā dienā notikumu nav", addEvent: "Pievienot notikumu", event: "Notikums", time: "Laiks", temperature: "Temperatūra",
    remove: "Dzēst", copyDay: "Kopēt dienu", copyTo: "Kopēt uz", copy: "Kopēt", unsaved: "Ir nesaglabātas izmaiņas",
    schedulerMode: "Kā darbojas grafiks", leave: "Iziet, nesaglabājot?", hours: "st.", minutes: "min",
    pin: "Servisa PIN", pinHint: "Tiek salīdzināts ar iekārtu un netiek saglabāts", pinWrong: "Nepareizs PIN", lock: "Aizvērt servisu",
    open: (t) => `Atvērts vēl ${t}`, needAdmin: "Serviss pieejams tikai administratoriem",
    active: "Tagad", history: "Vēsture", words: "Statusa vārdi", noFaults: "Bojājumu nav", noHistory: "Vēstures nav",
    resetErrors: "Atiestatīt kļūdas", clearHistory: "Notīrīt vēsturi", clearAsk: "Notīrīt vēsturi? Tā glabājas tikai Home Assistant.",
    appeared: "parādījās", cleared: "pazuda", kinds: { error: "Kļūda", warning: "Brīdinājums", alarm: "Trauksme" },
    bit: (w, b) => `${w}, bits ${b}`, flow: "Plūsmu shēma", clock: "Iekārtas pulkstenis", syncClock: "Iestatīt Home Assistant laiku",
    theme: "Tēma", themes: { auto: "Auto", light: "Gaiša", dark: "Tumša" }, accent: "Akcents", language: "Valoda",
    host: "Adrese", port: "Ports", unitId: "Modbus adrese", protocol: "Protokols", mac: "MAC", ip: "Iekārtas IP",
    firmware: "Programmatūra", bootloader: "Ielādētājs", eeprom: "EEPROM ieraksti", runningHours: "Darba stundas", exit: "Iziet no paneļa",
    menuButton: "Poga izvēlnē", leadsTo: "Kur tā ved",
    homeLayout: "Sākuma ekrāns", layouts: { house: "Māja", fan: "Ventilators" }, fanSpeed: "Ventilatoru ātrums",
    closesOnPick: "aizveras pēc izvēles", tapOutside: "pieskarieties ārpusē",
    errors: {
      forbidden: "Vajadzīgas administratora tiesības", service_locked: "Serviss aizvērts, ievadiet PIN vēlreiz",
      wrong_pin: "Nepareizs PIN", too_many_tries: (s) => `Pārāk daudz mēģinājumu, pagaidiet ${s} s`,
      unit_error: "Iekārta neatbildēja", invalid_value: "Nederīga vērtība", other: "Neizdevās",
    },
    units: { rpm: "apgr./min", "m³/h": "m³/h", d: "d.", h: "st.", min: "min", s: "s", Pa: "Pa", V: "V", mA: "mA" },
  },
  en: {
    locale: "en-GB",
    modes: ["Off", "Unoccupied", "Economy", "Comfort", "Boost", "Hood"],
    scheduleModes: ["Not used", "Standby", "Unoccupied", "Economy", "Comfort", "Boost"],
    onSchedule: "on schedule", manual: "manual", temporary: "temporary",
    scheduleMode: "Schedule", turnOff: "Turn off", mode: "Mode", menu: "Menu",
    outdoor: "From outside", supply: "Supply", extract: "Extract", exhaust: "Exhaust",
    toRooms: "To rooms", fromRooms: "From rooms", fan: "Fans", air: "Air", humidity: "Humidity",
    recovery: "Recovery", filter: "Filter", target: "target", now: "now", phases: ["heating", "recovery", "cooling"],
    offline: "The unit is not responding", loading: "Loading…", noUnit: "No unit is connected",
    on: "On", off: "Off", run: "Run", ok: "Done", cancel: "Cancel", confirm: "Continue", save: "Save",
    saved: "Saved", adminOnly: "Only administrators can change this", range: (a, b) => `${a} to ${b}`, factory: "factory",
    dangerSet: "A wrong value can stop the unit or cut the connection to it.",
    dangerRun: "This runs at once and can stop the unit.",
    filterAsk: "Reset the filter timer? Do this after changing the filter.",
    settings: (n) => `${n} settings`, sections: (n) => `${n} sections`,
    week: "Week", days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    daysShort: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    notRunning: "Manual control now, so the schedule is not running", turnOn: "Turn on",
    noEvents: "No events on this day", addEvent: "Add event", event: "Event", time: "Time", temperature: "Temperature",
    remove: "Remove", copyDay: "Copy this day", copyTo: "Copy to", copy: "Copy", unsaved: "There are unsaved changes",
    schedulerMode: "How the schedule works", leave: "Leave without saving?", hours: "h", minutes: "min",
    pin: "Service PIN", pinHint: "Checked against the unit and not stored", pinWrong: "Wrong PIN", lock: "Close service",
    open: (t) => `Open for ${t}`, needAdmin: "Service is for administrators only",
    active: "Now", history: "History", words: "Status words", noFaults: "No faults", noHistory: "No history yet",
    resetErrors: "Reset errors", clearHistory: "Clear history", clearAsk: "Clear the history? It is kept only in Home Assistant.",
    appeared: "appeared", cleared: "cleared", kinds: { error: "Error", warning: "Warning", alarm: "Alarm" },
    bit: (w, b) => `${w}, bit ${b}`, flow: "Air flow", clock: "Unit clock", syncClock: "Set to Home Assistant time",
    theme: "Theme", themes: { auto: "Auto", light: "Light", dark: "Dark" }, accent: "Accent", language: "Language",
    host: "Address", port: "Port", unitId: "Modbus unit ID", protocol: "Protocol", mac: "MAC", ip: "Unit IP",
    firmware: "Firmware", bootloader: "Bootloader", eeprom: "EEPROM writes", runningHours: "Running hours", exit: "Leave the panel",
    menuButton: "Menu button", leadsTo: "Where it leads",
    homeLayout: "Home screen", layouts: { house: "House", fan: "Fan" }, fanSpeed: "Fan speed",
    closesOnPick: "closes when you pick", tapOutside: "tap outside to close",
    errors: {
      forbidden: "This takes an administrator", service_locked: "Service has closed, enter the PIN again",
      wrong_pin: "Wrong PIN", too_many_tries: (s) => `Too many tries, wait ${s} s`,
      unit_error: "The unit did not answer", invalid_value: "That value is not allowed", other: "That did not work",
    },
    units: { d: "days" },
  },
};

// names of the menu's entries: [ru, lv, en]
const TITLES = {
  mode: ["Режим", "Režīms", "Mode"],
  climate: ["Климат", "Klimats", "Climate"],
  targets: ["Уставки температуры", "Temperatūras iestatījumi", "Temperature targets"],
  season: ["Сезон", "Sezona", "Season"],
  freecool: ["Свободное охлаждение", "Brīvā dzesēšana", "Free cooling"],
  sequence: ["Ступени нагрева и охлаждения", "Apsildes un dzesēšanas pakāpes", "Heating and cooling stages"],
  influence: ["Влияние на вентиляторы", "Ietekme uz ventilatoriem", "Effect on the fans"],
  extract: ["Регулирование по вытяжке", "Regulēšana pēc nosūces", "Control by extract air"],
  vent: ["Вентиляция", "Ventilācija", "Ventilation"],
  speeds: ["Скорости вентиляторов", "Ventilatoru ātrumi", "Fan speeds"],
  speedSupply: ["Приточный вентилятор", "Pieplūdes ventilators", "Supply fan"],
  speedExhaust: ["Вытяжной вентилятор", "Nosūces ventilators", "Extract fan"],
  fanMethod: ["Способ управления", "Vadības veids", "Control method"],
  airflow: ["Постоянный расход", "Nemainīga plūsma", "Constant airflow"],
  flowSupply: ["Расход притока", "Pieplūdes plūsma", "Supply airflow"],
  flowExhaust: ["Расход вытяжки", "Nosūces plūsma", "Extract airflow"],
  pressure: ["Постоянное давление", "Nemainīgs spiediens", "Constant pressure"],
  pressSupply: ["Давление притока", "Pieplūdes spiediens", "Supply pressure"],
  pressExhaust: ["Давление вытяжки", "Nosūces spiediens", "Extract pressure"],
  pressCommon: ["Общие настройки", "Kopīgie iestatījumi", "Common settings"],
  temporary: ["Временные режимы", "Pagaidu režīmi", "Temporary modes"],
  tempMode: ["Режим установки", "Iekārtas režīms", "Unit mode"],
  tempSpeed: ["Скорость", "Ātrums", "Speed"],
  tempHood: ["Вытяжка", "Nosūcējs", "Hood"],
  hood: ["Кухонная вытяжка", "Virtuves nosūcējs", "Cooker hood"],
  air: ["Качество воздуха", "Gaisa kvalitāte", "Air quality"],
  co2: ["CO₂", "CO₂", "CO₂"],
  humidity: ["Влажность", "Mitrums", "Humidity"],
  dry: ["Защита от пересушивания", "Aizsardzība pret izžūšanu", "Dry air protection"],
  schedule: ["Расписание", "Grafiks", "Schedule"],
  readings: ["Показания", "Rādījumi", "Readings"],
  faults: ["Ошибки", "Kļūdas", "Faults"],
  system: ["Система", "Sistēma", "System"],
  filter: ["Фильтр", "Filtrs", "Filter"],
  time: ["Дата и время", "Datums un laiks", "Date and time"],
  control: ["Управление", "Vadība", "Control"],
  display: ["Дисплей и Bluetooth", "Displejs un Bluetooth", "Display and Bluetooth"],
  screen: ["Экран панели", "Paneļa ekrāns", "Panel screen"],
  about: ["Об установке", "Par iekārtu", "About the unit"],
  service: ["Сервис", "Serviss", "Service"],
  maintenance: ["Обслуживание", "Apkope", "Maintenance"],
  fanhw: ["Вентиляторы: оборудование", "Ventilatoru aparatūra", "Fan hardware"],
  fan1: ["Вентилятор 1", "Ventilators 1", "Fan 1"],
  fan2: ["Вентилятор 2", "Ventilators 2", "Fan 2"],
  tempsensors: ["Датчики температуры", "Temperatūras sensori", "Temperature sensors"],
  beta: ["Коэффициенты B", "B koeficienti", "B coefficients"],
  adjust: ["Поправки", "Korekcijas", "Corrections"],
  limits: ["Пределы аварий", "Trauksmes robežas", "Alarm limits"],
  failure: ["При отказе датчика", "Sensora atteices gadījumā", "On sensor failure"],
  pressuresensors: ["Датчики давления", "Spiediena sensori", "Pressure sensors"],
  pressgeneral: ["Коэффициенты", "Koeficienti", "Factors"],
  averaging: ["Усреднение", "Vidējošana", "Averaging"],
  analog: ["Аналоговые входы", "Analogās ieejas", "Analog inputs"],
  ai1: ["Вход AI1", "Ieeja AI1", "Input AI1"],
  ai2: ["Вход AI2", "Ieeja AI2", "Input AI2"],
  ai3: ["Вход AI3", "Ieeja AI3", "Input AI3"],
  digital: ["Цифровые входы", "Digitālās ieejas", "Digital inputs"],
  dampers: ["Клапаны и заслонки", "Vārsti un aizbīdņi", "Dampers"],
  fire: ["Пожарная защита", "Ugunsdrošība", "Fire protection"],
  coils: ["Нагрев и охлаждение", "Apsilde un dzesēšana", "Heating and cooling"],
  coil1: ["Калорифер 1", "Kalorifers 1", "Coil 1"],
  coil2: ["Калорифер 2", "Kalorifers 2", "Coil 2"],
  preheater: ["Нагреватели", "Sildītāji", "Heaters"],
  combined: ["Комбинированный калорифер", "Kombinētais kalorifers", "Combined coil"],
  recovery: ["Рекуперация", "Siltuma atguve", "Heat recovery"],
  exchanger: ["Теплообменник", "Siltummainis", "Exchanger"],
  rotor: ["Ротор", "Rotors", "Rotor"],
  bypass: ["Байпас", "Apvads", "Bypass"],
  deicing: ["Оттайка", "Atkausēšana", "De-icing"],
  pid: ["Регуляторы", "Regulatori", "Controllers"],
  pidSupply: ["Приток", "Pieplūde", "Supply"],
  pidExtract: ["Вытяжка", "Nosūce", "Extract"],
  pidFlow: ["Постоянный расход", "Nemainīga plūsma", "Constant airflow"],
  pidPress: ["Постоянное давление", "Nemainīgs spiediens", "Constant pressure"],
  pidCo2: ["CO₂", "CO₂", "CO₂"],
  pidHum: ["Влажность", "Mitrums", "Humidity"],
  unit: ["Общие параметры", "Vispārīgie parametri", "General"],
  network: ["Сеть", "Tīkls", "Network"],
  netAddress: ["IP-адрес", "IP adrese", "IP address"],
  netGateway: ["Шлюз", "Vārteja", "Gateway"],
  netMask: ["Маска", "Tīkla maska", "Subnet mask"],
  netDns: ["DNS", "DNS", "DNS"],
  netModbus: ["Modbus TCP", "Modbus TCP", "Modbus TCP"],
  fieldbus: ["Шина", "Kopne", "Fieldbus"],
  hmi: ["HMI", "HMI", "HMI"],
  rtu1: ["RTU1", "RTU1", "RTU1"],
  rtu2: ["RTU2", "RTU2", "RTU2"],
  // readings
  r_temperature: ["Температура", "Temperatūra", "Temperature"],
  r_air: ["Воздух", "Gaiss", "Air"],
  r_fans: ["Вентиляторы", "Ventilatori", "Fans"],
  r_operation: ["Работа", "Darbība", "Operation"],
  r_coils: ["Нагрев и охлаждение", "Apsilde un dzesēšana", "Heating and cooling"],
  r_dampers: ["Клапаны", "Vārsti", "Dampers"],
  r_inputs: ["Входы", "Ieejas", "Inputs"],
  r_temporary: ["Временные режимы", "Pagaidu režīmi", "Temporary modes"],
  r_schedule: ["Расписание", "Grafiks", "Schedule"],
  r_system: ["Система", "Sistēma", "System"],
  r_device: ["Устройство", "Ierīce", "Device"],
};

const MODE_FIELDS = "Unoccupied|Economy|Comfort|Boost|Kitchen[Hh]ood";

// the menu; a leaf lists the settings its pattern matches, kids make a submenu
const TREE = [
  { id: "mode", icon: "power", view: "modes" },
  {
    id: "climate", icon: "thermo", kids: [
      { id: "targets", icon: "thermo", match: /^AirTemp_(SupplyTarget_|ExtractTarget_|MinAllowed|MaxAllowed)/ },
      { id: "season", icon: "sun", match: /^AirTemp_Season_/ },
      { id: "freecool", icon: "snow", match: /^FreeCooling_/ },
      { id: "sequence", icon: "bolt", match: /^AirTemp_(Heat|Cool)Sequence_/ },
      { id: "influence", icon: "fan", match: /^AirTemp_FanInfluence_/ },
      { id: "extract", icon: "sliders", match: /^AirTemp_ExtractControl_Max/ },
    ],
  },
  {
    id: "vent", icon: "fan", kids: [
      { id: "fanMethod", icon: "sliders", match: /^(Fans_ControlStrategy|External_0to10V_FanRatio)$/ },
      {
        id: "speeds", icon: "fan", kids: [
          { id: "speedSupply", icon: "fan", match: /^Linear_Fan1_/ },
          { id: "speedExhaust", icon: "fan", match: /^Linear_Fan2_/ },
        ],
      },
      {
        id: "airflow", icon: "gauge", kids: [
          { id: "flowSupply", icon: "gauge", match: new RegExp(`^Constant_Airflow_Fan1_(${MODE_FIELDS})$`) },
          { id: "flowExhaust", icon: "gauge", match: new RegExp(`^Constant_Airflow_Fan2_(${MODE_FIELDS})$`) },
        ],
      },
      {
        id: "pressure", icon: "gauge", kids: [
          { id: "pressCommon", icon: "sliders", match: /^Constant_Pressure_(Duct|Master)/ },
          { id: "pressSupply", icon: "gauge", match: new RegExp(`^Constant_Pressure_Fan1_(${MODE_FIELDS})$`) },
          { id: "pressExhaust", icon: "gauge", match: new RegExp(`^Constant_Pressure_Fan2_(${MODE_FIELDS})$`) },
        ],
      },
      {
        id: "temporary", icon: "clock", kids: [
          { id: "tempMode", icon: "power", match: /^Temp_SystemMode_/ },
          { id: "tempSpeed", icon: "fan", match: /^Temp_FanSpeed_/ },
          { id: "tempHood", icon: "hood", match: /^Temp_KitchenHood_/ },
        ],
      },
      { id: "hood", icon: "hood", match: /^CH_/ },
    ],
  },
  {
    id: "air", icon: "leaf", kids: [
      { id: "co2", icon: "leaf", match: /^AirQ_CO2_(Enable|Target_)/ },
      { id: "humidity", icon: "drop", match: /^AirQ_Humidity_(Enable|Target_)/ },
      { id: "dry", icon: "shield", match: /^AirQ_DryProt_/ },
    ],
  },
  { id: "schedule", icon: "calendar", view: "week" },
  { id: "readings", icon: "chart", view: "readings" },
  { id: "faults", icon: "alert", view: "faults" },
  {
    id: "system", icon: "sliders", kids: [
      { id: "filter", icon: "filter", match: /^Filter_/ },
      { id: "time", icon: "clock", clock: true, match: /^(TimeSync_|Timezone$|DST_)/ },
      { id: "control", icon: "power", match: /^(ControlMode|OperatingMode|BoostMode_Timer|ResetErrors)$/ },
      { id: "display", icon: "wifi", match: /^(Bluetooth_OnOff|DisplayLanguage)$/ },
      { id: "screen", icon: "palette", view: "screen" },
      { id: "about", icon: "info", view: "about" },
    ],
  },
  {
    id: "service", icon: "lock", service: true, kids: [
      { id: "maintenance", icon: "shield", match: /^(ResetEventLog|RestartUnit|Create_|Restore_)/ },
      { id: "unit", icon: "chip", match: /^(SystemStabilisingTime_StandbyToActive|UnitConfiguration|AirTemp_ControlStrategy)$/ },
      {
        id: "fanhw", icon: "fan", kids: [
          { id: "fan1", icon: "fan", match: /^Fan1_/ },
          { id: "fan2", icon: "fan", match: /^Fan2_/ },
        ],
      },
      {
        id: "tempsensors", icon: "thermo", kids: [
          { id: "beta", icon: "chip", match: /^TemperatureSensor_Beta_/ },
          { id: "adjust", icon: "sliders", match: /^T_.*_Adjust$/ },
          { id: "limits", icon: "alert", match: /^Temp_.*AlarmLimit$/ },
          { id: "failure", icon: "shield", match: /^SensorFailureAction_T_/ },
        ],
      },
      {
        id: "pressuresensors", icon: "gauge", kids: [
          { id: "pressgeneral", icon: "chip", match: /^(Airflow_K_Factor_|PressureSensorsPresent)/ },
          { id: "averaging", icon: "chart", match: /^(PressureSensorAveragingAlgorithm|MA_|EMA_|RateLimiter_)/ },
          { id: "adjust2", title: "adjust", icon: "sliders", match: /^Pressure\d_Adjust$/ },
          { id: "limits2", title: "limits", icon: "alert", match: /^Pressure\d_.*AlarmLimit$/ },
          { id: "failure2", title: "failure", icon: "shield", match: /^SensorFailureAction_Pressure/ },
        ],
      },
      {
        id: "analog", icon: "chip", kids: [
          { id: "ai1", icon: "chip", match: /^AI1_/ },
          { id: "ai2", icon: "chip", match: /^AI2_/ },
          { id: "ai3", icon: "chip", match: /^AI3_/ },
          { id: "adjust3", title: "adjust", icon: "sliders", match: /^AI_.*_Adjust$/ },
          { id: "failure3", title: "failure", icon: "shield", match: /^SensorFailureAction_AI_/ },
        ],
      },
      { id: "digital", icon: "chip", match: /^DI\d_/ },
      { id: "dampers", icon: "flow", match: /^(HBridge|Damper_Function|OutsideDamper_)/ },
      { id: "fire", icon: "alert", match: /^FireDamper_/ },
      {
        id: "coils", icon: "sun", kids: [
          { id: "coil1", icon: "sun", match: /^Coil1_/ },
          { id: "coil2", icon: "sun", match: /^Coil2_/ },
          { id: "preheater", icon: "bolt", match: /^(Preheater_|ElectricHeater_)/ },
          { id: "combined", icon: "flow", match: /^CombinedCoil_/ },
        ],
      },
      {
        id: "recovery", icon: "flow", kids: [
          { id: "exchanger", icon: "flow", match: /^AirTemp_ERC_(TypeInstalled|Passive_)/ },
          { id: "rotor", icon: "fan", match: /^AirTemp_ERC_Rotary_/ },
          { id: "bypass", icon: "sliders", match: /^Bypass_/ },
          { id: "deicing", icon: "snow", match: /^AirTemp_ERC_Deicing_/ },
        ],
      },
      {
        id: "pid", icon: "sliders", kids: [
          { id: "pidSupply", icon: "thermo", match: /^AirTemp_PhaseControl_/ },
          { id: "pidExtract", icon: "thermo", match: /^AirTemp_ExtractControl_(Coeff|PID)/ },
          { id: "pidFlow", icon: "gauge", match: /^Constant_Airflow_Fan\d_Coeff/ },
          { id: "pidPress", icon: "gauge", match: /^Constant_Pressure_Fan\d_Coeff/ },
          { id: "pidCo2", icon: "leaf", match: /^AirQ_CO2_Coeff/ },
          { id: "pidHum", icon: "drop", match: /^AirQ_Humidity_Coeff/ },
        ],
      },
      {
        id: "network", icon: "wifi", kids: [
          { id: "netAddress", icon: "wifi", match: /^ModbusTCP_(Static_IP|Device_IP)/ },
          { id: "netGateway", icon: "wifi", match: /^ModbusTCP_Gateway_/ },
          { id: "netMask", icon: "wifi", match: /^ModbusTCP_Subnet/ },
          { id: "netDns", icon: "wifi", match: /^ModbusTCP_DNS_/ },
          { id: "netModbus", icon: "chip", match: /^ModbusTCP_(ONOFF|Timeout|RTU|Port)$/ },
        ],
      },
      {
        id: "fieldbus", icon: "chip", kids: [
          { id: "hmi", icon: "chip", match: /^Modbus_HMI_/ },
          { id: "rtu1", icon: "chip", match: /^Modbus_RTU1_/ },
          { id: "rtu2", icon: "chip", match: /^(Modbus_RTU2_|RTU2_|TargetSlave_)/ },
        ],
      },
    ],
  },
];

const READINGS = {
  temperature: "thermo", air: "leaf", fans: "fan", operation: "power", coils: "sun", dampers: "flow",
  inputs: "chip", temporary: "clock", schedule: "calendar", system: "sliders", device: "info",
};

const or = (value, other) => (value === null || value === undefined ? other : value);
const esc = (text) =>
  String(or(text, "")).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const icon = (name, cls = "") => `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[name]}"/></svg>`;
const two = (n) => String(n).padStart(2, "0");
const minutes = (event) => event[0] * 60 + event[1];

const stored = {
  get(key) {
    try {
      return window.localStorage.getItem(`alpicair-wall-${key}`);
    } catch (err) {
      return null;
    }
  },
  set(key, value) {
    try {
      window.localStorage.setItem(`alpicair-wall-${key}`, value);
    } catch (err) {
      // private mode and previews have no storage; the choice then lasts until the page reloads
    }
  },
};

const STYLE = `
:host { display: block; position: relative; height: 100vh; overflow: hidden; background: #000; }
* { box-sizing: border-box; }
.app {
  position: relative; display: flex; flex-direction: column; width: ${BASE}px; height: ${BASE}px; overflow: hidden;
  font-family: var(--ha-font-family-body, Roboto, "Segoe UI", Helvetica, Arial, sans-serif); font-size: 16px; line-height: 1.25;
  color: var(--tx); background: var(--bg); font-variant-numeric: tabular-nums;
  -webkit-tap-highlight-color: transparent; -webkit-user-select: none; user-select: none;
}
.t-light {
  --bg: #eceff4; --sf: #fff; --sf2: #f5f7fa; --sf3: #e9edf2; --tx: #0f1724; --tx2: #5a6475; --tx3: #8a93a3;
  --track: rgba(15, 23, 36, .09); --sh: 0 1px 3px rgba(16, 24, 40, .08); --ov: rgba(15, 23, 36, .45);
  --roof: #3f4b5e; --attic: #f5f7fa; --wall: #fff; --line: rgba(15, 23, 36, .12); --ground: #c9d0da;
}
.t-dark {
  --bg: #0d1015; --sf: #171b22; --sf2: #1e232c; --sf3: #272d38; --tx: #f2f4f8; --tx2: #9aa3b2; --tx3: #687284;
  --track: rgba(255, 255, 255, .09); --sh: none; --ov: rgba(0, 0, 0, .6);
  --roof: #475569; --attic: #1b2029; --wall: #1e232c; --line: rgba(255, 255, 255, .1); --ground: #2a313c;
}
button { font: inherit; color: inherit; background: none; border: 0; padding: 0; margin: 0; text-align: inherit; cursor: pointer; outline: none; -webkit-tap-highlight-color: transparent; transition: transform .1s; }
button:active { transform: scale(.97); }
button[disabled] { opacity: .45; }
.ic { width: 24px; height: 24px; flex: none; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; }
.fwd { animation: in-fwd .16s ease-out; }
.rev { animation: in-rev .16s ease-out; }
@keyframes in-fwd { from { transform: translateX(28px); opacity: .4; } to { transform: none; opacity: 1; } }
@keyframes in-rev { from { transform: translateX(-28px); opacity: .4; } to { transform: none; opacity: 1; } }
.off-bar { flex: none; padding: 6px 12px; background: #ef4444; color: #fff; font-size: 14px; text-align: center; }

/* header of every screen but home */
.bar { flex: none; display: flex; align-items: center; height: 64px; padding: 8px 10px; }
.bar .tap { width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; border-radius: 16px; background: var(--sf); box-shadow: var(--sh); flex: none; }
.bar-text { flex: 1; min-width: 0; margin: 0 12px; }
.bar-text b { display: block; font-size: 20px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-text span { display: block; margin-top: 1px; color: var(--tx2); font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.body { flex: 1; min-height: 0; padding: 0 10px 10px; overflow-x: hidden; overflow-y: auto; -webkit-overflow-scrolling: touch; }
.body::-webkit-scrollbar { width: 0; height: 0; }

/* home */
.home { display: flex; flex-direction: column; height: 100%; padding: 10px; }
.top { flex: none; display: flex; align-items: center; height: 52px; padding: 0 6px; }
.top .state { flex: 1; min-width: 0; }
.top b { display: block; font-size: 24px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top span { display: block; color: var(--tx2); font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.badge { display: flex; align-items: center; height: 36px; margin-right: 10px; padding: 0 10px; border-radius: 18px; background: rgba(239, 68, 68, .14); color: #ef4444; font-weight: 600; }
.badge .ic { width: 20px; height: 20px; margin-right: 5px; }
.badge.warn { background: rgba(245, 158, 11, .16); color: #d97706; }
.time { font-size: 28px; font-weight: 300; }
.top .tap { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; margin-right: 10px; border-radius: 14px; background: var(--sf); box-shadow: var(--sh); flex: none; }
.fan-card { flex: 1; min-height: 0; display: flex; align-items: stretch; margin-top: 8px; padding: 10px; background: var(--sf); border-radius: 24px; box-shadow: var(--sh); }
.fan-side { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; text-align: center; }
.fan-who { flex: none; padding: 2px 0 8px; }
.fan-who span { display: block; color: var(--tx2); font-size: 13px; }
.fan-who b { display: block; font-size: 22px; font-weight: 500; }
.fan-who small { display: block; color: var(--tx2); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fan-step { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; border-radius: 18px; background: rgba(var(--acc-rgb), .13); color: var(--acc); }
.fan-step .ic { width: 40px; height: 40px; stroke-width: 2.4; }
.ring-tap { flex: none; align-self: center; margin: 0 6px; }
.ring { position: relative; width: 204px; height: 204px; }
.ring.large { width: 262px; height: 262px; }
.ring svg { display: block; width: 100%; height: 100%; }
.ring-track, .ring-value { fill: none; stroke-width: 11; stroke-linecap: round; }
.ring-track { stroke: var(--track); }
.ring-value { stroke: var(--acc); transition: stroke-dasharray .25s ease-out; }
.ring-dot { fill: var(--sf); stroke: var(--tx); stroke-width: 3; }
.ring-text { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; pointer-events: none; }
.ring-text b { font-size: 58px; font-weight: 300; line-height: 1.1; letter-spacing: -1px; }
.ring-text b small { margin-left: 2px; font-size: 22px; font-weight: 400; color: var(--tx2); letter-spacing: 0; }
.ring-text b.tight { font-size: 44px; }
.ring-text b.tight small { font-size: 15px; }
.ring-text span { margin-top: 2px; color: var(--tx2); font-size: 13px; }
.ring-text .ring-mode { max-width: 150px; margin-top: 4px; color: var(--tx); font-size: 16px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ring-text .fan-wrap { display: block; width: 26px; height: 26px; margin: 0 0 2px; color: var(--acc); }
.ring-text .fan-wrap .ic { width: 26px; height: 26px; }
.ring-card { display: flex; flex-direction: column; align-items: center; justify-content: space-between; height: 100%; padding: 14px; background: var(--sf); border-radius: 24px; box-shadow: var(--sh); }
.ring-buttons { display: flex; width: 100%; }
.ring-buttons button { flex: 1; height: 72px; display: flex; align-items: center; justify-content: center; background: var(--sf3); border-radius: 18px; }
.ring-buttons button + button { margin-left: 8px; }
.temps { flex: none; display: flex; height: 62px; margin-top: 8px; background: var(--sf); border-radius: 20px; box-shadow: var(--sh); }
.temp-cell { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; justify-content: center; padding-left: 12px; border-right: 1px solid var(--track); }
.temp-cell:last-child { border-right: 0; }
.temp-cell span { display: flex; align-items: center; color: var(--tx2); font-size: 12px; white-space: nowrap; overflow: hidden; }
.temp-cell span i { flex: none; display: inline-block; width: 8px; height: 8px; margin-right: 5px; border-radius: 50%; }
.temp-cell b { display: block; margin-top: 1px; font-size: 21px; font-weight: 400; }
.fresh { background: #38bdf8; } .stale { background: #f97316; }
.dock { flex: none; display: flex; height: 84px; margin-top: 8px; }
.dock button { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; justify-content: center; padding: 8px 10px; background: var(--sf); border-radius: 20px; box-shadow: var(--sh); }
.dock button + button { margin-left: 8px; }
.dock span { display: block; color: var(--tx2); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dock b { display: block; margin-top: 2px; font-size: 16px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dock .ic { width: 22px; height: 22px; color: var(--acc); }
.dock .accent .ic { color: #fff; }
.dock .accent { background: var(--acc); color: #fff; }
.dock .accent span { color: rgba(255, 255, 255, .85); }
.spin { animation: spin var(--speed, 2s) linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* home: the house */
.house-wrap { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; }
.house { position: relative; width: 460px; height: 352px; flex: none; }
.house > svg { position: absolute; top: 0; left: 0; width: 460px; height: 352px; }
.house .clock { position: absolute; left: 150px; top: 4px; width: 160px; text-align: center; font-size: 24px; font-weight: 700; }
.house .badge { position: absolute; right: 0; top: 0; height: 40px; margin: 0; padding: 0 12px; border-radius: 20px; font-size: 17px; font-weight: 700; }
.house .tap { position: absolute; left: 104px; top: 0; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 14px; background: var(--sf); box-shadow: var(--sh); }
.hl { position: absolute; width: 80px; text-align: center; font-size: 32px; font-weight: 500; line-height: 1.1; white-space: nowrap; }
.house-mid { position: absolute; left: 150px; top: 180px; width: 160px; display: flex; flex-direction: column; align-items: center; }
.house-speed { display: flex; align-items: baseline; justify-content: center; min-width: 120px; height: 55px; border-radius: 16px; }
.house-speed b { font-size: 56px; font-weight: 300; letter-spacing: -1px; line-height: 1; }
.house-speed small { margin-left: 2px; font-size: 20px; color: var(--tx2); }
.house-mode { display: flex; align-items: center; justify-content: center; min-width: 116px; max-width: 160px; height: 63px; margin-top: 4px; padding: 0 14px; border-radius: 18px; background: rgba(var(--acc-rgb), .12); font-size: 15px; font-weight: 600; }
.house-mode .ic { width: 16px; height: 16px; margin-right: 6px; }
.house-mode span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dock.tall { height: 98px; margin-top: 10px; }
.dock.tall b { font-size: 18px; }

/* half-transparent sheets over the home screen */
.sheet-shade { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 4; display: flex; align-items: flex-end; background: var(--ov); }
.sheet { width: 100%; padding: 16px 16px 18px; border-radius: 26px 26px 0 0; background: var(--sf); animation: sheet-up .18s ease-out; }
@keyframes sheet-up { from { transform: translateY(40px); } to { transform: none; } }
.sheet-head { display: flex; align-items: center; justify-content: space-between; margin: 0 4px 12px; }
.sheet-head b { font-size: 18px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sheet-head span { flex: none; margin-left: 10px; color: var(--tx2); font-size: 13px; }
.picks { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-gap: 8px; }
.pick { display: flex; flex-direction: column; justify-content: center; height: 56px; padding: 0 14px; border-radius: 16px; background: var(--sf3); }
.pick b { font-size: 15px; font-weight: 600; }
.pick span { font-size: 12px; opacity: .75; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pick.span { grid-column: 1 / -1; }
.pick.on { background: var(--acc); color: #fff; }
.sheet-row { display: flex; align-items: center; }
.sheet-step { flex: 1 1 0; height: 120px; display: flex; align-items: center; justify-content: center; border-radius: 20px; background: rgba(var(--acc-rgb), .13); color: var(--acc); }
.sheet-step .ic { width: 36px; height: 36px; stroke-width: 2.4; }
.sheet-step.low { height: 96px; }
.sheet-mid { flex: none; width: 170px; margin: 0 12px; text-align: center; }
.ring.small { width: 170px; height: 170px; }
.ring.small .ring-text b { font-size: 44px; }
.ring.small .ring-text b small { font-size: 18px; }
.sheet-mid > b { font-size: 60px; font-weight: 300; letter-spacing: -1px; }
.sheet-mid > b small { font-size: 22px; font-weight: 400; color: var(--tx2); }
.bar-line { height: 8px; margin-top: 6px; border-radius: 4px; background: var(--sf3); overflow: hidden; }
.bar-line i { display: block; height: 100%; width: 0; background: var(--acc); transition: width .2s; }

/* main menu */
.grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-template-rows: repeat(3, minmax(0, 1fr)); grid-gap: 8px; height: 100%; }
.tile { position: relative; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; padding: 12px; background: var(--sf); border-radius: 22px; box-shadow: var(--sh); overflow: hidden; }
.tile .box { width: 42px; height: 42px; }
.tile b { display: block; font-size: 15px; font-weight: 600; line-height: 1.15; }
.tile span { display: block; margin-top: 2px; color: var(--tx2); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile .count { position: absolute; top: 12px; right: 12px; min-width: 24px; height: 24px; padding: 0 6px; border-radius: 12px; background: #ef4444; color: #fff; font-size: 13px; font-weight: 600; line-height: 24px; text-align: center; }
.box { display: flex; align-items: center; justify-content: center; width: 44px; height: 44px; flex: none; border-radius: 14px; background: rgba(var(--acc-rgb), .13); color: var(--acc); }
.grid.short { height: calc(100% - 64px); }
.grid.short .tile { padding: 9px 12px; }
.grid.short .tile .box { width: 36px; height: 36px; border-radius: 12px; }
.grid.short .tile .box .ic { width: 22px; height: 22px; }
.leave { display: flex; height: 56px; margin-top: 8px; }
.leave button { display: flex; align-items: center; justify-content: center; height: 100%; border-radius: 18px; }
.leave .out { flex: 1 1 0; min-width: 0; padding: 0 14px; background: var(--acc); color: #fff; }
.leave .out b { margin-left: 8px; font-size: 17px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.leave .set { flex: none; width: 56px; margin-left: 8px; background: var(--sf); box-shadow: var(--sh); }

/* lists */
.group { margin-bottom: 8px; background: var(--sf); border-radius: 20px; box-shadow: var(--sh); overflow: hidden; }
.row { position: relative; display: flex; align-items: center; width: 100%; min-height: 66px; padding: 9px 14px; }
.row + .row::before { content: ""; position: absolute; top: 0; left: 14px; right: 14px; height: 1px; background: var(--track); }
.row .box { margin-right: 12px; }
.row-text { flex: 1; min-width: 0; }
.row-text b { display: block; font-size: 16px; font-weight: 500; word-break: break-word; }
.row-text span { display: block; margin-top: 2px; color: var(--tx2); font-size: 13px; word-break: break-word; }
.row-value { flex: none; max-width: 46%; margin-left: 10px; color: var(--tx2); font-size: 16px; text-align: right; word-break: break-word; }
.row .go { margin-left: 4px; color: var(--tx3); width: 20px; height: 20px; }
.toggle { position: relative; flex: none; width: 52px; height: 30px; margin-left: 10px; }
.toggle input { position: absolute; top: 0; left: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer; }
.toggle i { position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: 15px; background: var(--sf3); pointer-events: none; transition: background .15s; }
.toggle i::after { content: ""; position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, .3); transition: transform .15s; }
.toggle input:checked + i { background: var(--acc); }
.toggle input:checked + i::after { transform: translateX(22px); }
.pill { flex: none; height: 44px; margin-left: 10px; padding: 0 16px; border-radius: 14px; background: rgba(var(--acc-rgb), .13); color: var(--acc); font-weight: 600; }
.pill.danger { background: rgba(239, 68, 68, .13); color: #ef4444; }
.wide { display: flex; align-items: center; justify-content: center; width: 100%; height: 56px; margin-bottom: 8px; border-radius: 18px; background: var(--acc); color: #fff; font-size: 17px; font-weight: 600; text-align: center; }
.wide.soft { background: var(--sf); color: var(--tx); box-shadow: var(--sh); }
.wide.danger { background: rgba(239, 68, 68, .13); color: #ef4444; box-shadow: none; }
.wide .ic { margin-right: 8px; }
.note { margin-bottom: 8px; padding: 12px 14px; border-radius: 18px; background: rgba(245, 158, 11, .15); font-size: 14px; }
.empty { padding: 36px 16px; color: var(--tx2); text-align: center; }
.lamp { display: inline-block; width: 11px; height: 11px; margin-right: 6px; border-radius: 50%; background: var(--sf3); }
.lamp.on { background: #22c55e; }

/* modes */
.modes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); grid-gap: 8px; }
.mode { display: flex; align-items: center; height: 88px; padding: 12px; background: var(--sf); border-radius: 22px; box-shadow: var(--sh); }
.mode.span { grid-column: 1 / -1; height: 72px; }
.mode .box { margin-right: 10px; }
.mode b { display: block; font-size: 16px; font-weight: 600; }
.mode span { display: block; margin-top: 2px; color: var(--tx2); font-size: 13px; }
.mode.on { background: var(--acc); color: #fff; }
.mode.on .box { background: rgba(255, 255, 255, .22); color: #fff; }
.mode.on span { color: rgba(255, 255, 255, .85); }

/* editor */
.big { flex: none; padding: 6px 0 2px; text-align: center; }
.big button { min-width: 200px; padding: 2px 12px; border-radius: 16px; }
.big b { font-size: 56px; font-weight: 300; letter-spacing: -1px; }
.big small { margin-left: 4px; color: var(--tx2); font-size: 20px; letter-spacing: 0; }
.limits { flex: none; color: var(--tx2); font-size: 13px; text-align: center; }
.slider { flex: none; padding: 18px 8px 10px; }
input[type="range"] { display: block; width: 100%; height: 40px; margin: 0; background: none; -webkit-appearance: none; outline: none; }
input[type="range"]::-webkit-slider-runnable-track { height: 12px; border-radius: 6px; background: var(--sf3); }
input[type="range"]::-webkit-slider-thumb { width: 36px; height: 36px; margin-top: -12px; border-radius: 50%; background: var(--acc); border: 4px solid var(--sf); box-shadow: 0 1px 4px rgba(0, 0, 0, .3); -webkit-appearance: none; }
.steps { flex: none; display: flex; padding: 4px 0 8px; }
.steps button { flex: 1; height: 68px; display: flex; align-items: center; justify-content: center; border-radius: 20px; background: var(--sf); box-shadow: var(--sh); }
.steps button + button { margin-left: 8px; }
.steps .ic { width: 30px; height: 30px; }
.foot { flex: none; display: flex; padding-top: 4px; }
.foot button { flex: 1; height: 60px; display: flex; align-items: center; justify-content: center; border-radius: 18px; background: var(--sf); box-shadow: var(--sh); font-size: 17px; font-weight: 600; }
.foot button + button { margin-left: 8px; }
.foot .main { background: var(--acc); color: #fff; }
.editor { display: flex; flex-direction: column; height: 100%; }
.grow { flex: 1; min-height: 0; }
.keys { flex: none; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-gap: 6px; padding: 6px 0; }
.keys button { height: 58px; display: flex; align-items: center; justify-content: center; border-radius: 16px; background: var(--sf); box-shadow: var(--sh); font-size: 24px; }
.keys .main { background: var(--acc); color: #fff; font-size: 17px; font-weight: 600; }
.keys.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.keys.four button { height: 52px; }
.keys .all { grid-column: 1 / -1; }
.dots { flex: none; display: flex; justify-content: center; padding: 8px 0; }
.dots i { width: 18px; height: 18px; margin: 0 8px; border-radius: 50%; border: 2px solid var(--tx3); }
.dots i.on { background: var(--acc); border-color: var(--acc); }

/* schedule */
.day { display: flex; align-items: center; width: 100%; height: 42px; padding: 0 12px; }
.day b { width: 34px; flex: none; font-size: 14px; font-weight: 600; }
.line { position: relative; flex: 1; height: 18px; border-radius: 6px; background: var(--sf3); overflow: hidden; }
.line i { position: absolute; top: 0; bottom: 0; }
.m1 { background: #94a3b8; } .m2 { background: #38bdf8; } .m3 { background: #22c55e; } .m4 { background: #f59e0b; } .m5 { background: #ef4444; }
.scale { display: flex; justify-content: space-between; padding: 0 12px 8px 46px; color: var(--tx3); font-size: 11px; }
.legend { display: flex; flex-wrap: wrap; padding: 2px 12px 10px; color: var(--tx2); font-size: 12px; }
.legend span { display: flex; align-items: center; margin: 0 10px 2px 0; }
.legend i { width: 10px; height: 10px; margin-right: 4px; border-radius: 3px; }
.chipm { display: inline-block; width: 12px; height: 12px; margin-right: 6px; border-radius: 4px; }
.chips { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-gap: 6px; margin-bottom: 6px; }
.chips button { height: 46px; display: flex; align-items: center; justify-content: center; padding: 0 4px; border-radius: 14px; background: var(--sf); box-shadow: var(--sh); font-size: 14px; text-align: center; }
.chips button.on { background: var(--acc); color: #fff; }
.field { display: flex; align-items: center; height: 62px; margin-bottom: 6px; padding: 0 6px; background: var(--sf); border-radius: 18px; box-shadow: var(--sh); }
.field > span { flex: 1; padding-left: 8px; color: var(--tx2); font-size: 15px; }
.field > b { width: 84px; font-size: 30px; font-weight: 300; text-align: center; }
.field button { width: 56px; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 14px; background: var(--sf3); }

/* flow */
.scheme { position: relative; height: 236px; margin-bottom: 8px; background: var(--sf); border-radius: 22px; box-shadow: var(--sh); }
.scheme svg { position: absolute; top: 12px; left: 8px; width: 448px; height: 212px; }
.line-fresh, .line-stale { fill: none; stroke-width: 9; stroke-linecap: round; }
.line-fresh { stroke: #38bdf8; } .line-stale { stroke: #f97316; }
.body-unit { fill: var(--sf2); stroke: var(--track); stroke-width: 2; }
.core { fill: var(--sf); stroke: var(--tx3); stroke-width: 2; }
.core-text { fill: var(--tx); font-size: 26px; font-weight: 500; text-anchor: middle; }
.port { position: absolute; padding: 2px 4px; }
.port b { display: block; font-size: 22px; font-weight: 400; }
.port span { display: block; color: var(--tx2); font-size: 12px; }
.port.tl { top: 8px; left: 12px; } .port.tr { top: 8px; right: 12px; text-align: right; }
.port.bl { bottom: 8px; left: 12px; } .port.br { bottom: 8px; right: 12px; text-align: right; }
.pair { display: flex; margin-bottom: 8px; }
.pair > div { flex: 1 1 0; min-width: 0; padding: 12px 14px; background: var(--sf); border-radius: 20px; box-shadow: var(--sh); }
.pair > div + div { margin-left: 8px; }
.pair span { display: block; color: var(--tx2); font-size: 13px; }
.pair b { display: block; font-size: 24px; font-weight: 400; }
.pair small { display: block; color: var(--tx2); font-size: 13px; }

/* faults */
.kind { display: inline-block; flex: none; margin-right: 10px; padding: 3px 10px; border-radius: 12px; background: #ef4444; color: #fff; font-size: 12px; }
.kind.warning { background: #f59e0b; color: #1b1b1b; }
.kind.alarm { background: #f97316; }
.kind.gone { background: var(--sf3); color: var(--tx2); }
.words { padding: 12px 14px; font-family: var(--code-font-family, monospace); font-size: 14px; line-height: 1.5; }

/* screen settings */
.seg { display: flex; margin-bottom: 8px; padding: 4px; background: var(--sf); border-radius: 18px; box-shadow: var(--sh); }
.seg button { flex: 1 1 0; min-width: 0; height: 50px; display: flex; align-items: center; justify-content: center; border-radius: 14px; font-size: 15px; }
.seg button.on { background: var(--acc); color: #fff; font-weight: 600; }
.caption { margin: 6px 6px 6px; color: var(--tx2); font-size: 13px; }
.swatches { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); grid-gap: 8px; margin-bottom: 8px; }
.swatches button { height: 54px; display: flex; align-items: center; justify-content: center; border-radius: 16px; color: #fff; }

/* overlays */
.shade { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 5; display: flex; align-items: center; justify-content: center; padding: 20px; background: var(--ov); }
.ask { width: 100%; padding: 20px; background: var(--sf); border-radius: 26px; }
.ask p { margin: 0 0 18px; font-size: 18px; line-height: 1.35; }
.ask .small { margin-top: -10px; color: var(--tx2); font-size: 14px; }
.toast { position: absolute; left: 50%; bottom: 16px; z-index: 6; max-width: 440px; padding: 10px 18px; border-radius: 16px; background: #1f2937; color: #fff; font-size: 15px; transform: translateX(-50%); white-space: nowrap; }
.center { display: flex; align-items: center; justify-content: center; height: 100%; padding: 24px; color: var(--tx2); text-align: center; }
`;

class AlpicAirNestWall extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._stack = [{ view: "home" }];
    this._dp = {};
    this._sp = {};
    this._status = { available: true, virtual: {}, faults: [], words: {} };
    this._last = Date.now();
    this._token = null;
    this._tokenUntil = 0;
    this._pendingTarget = null;
    this._nodes = {};
    const index = (nodes, parent, service) => {
      nodes.forEach((node) => {
        const entry = Object.assign({}, node, { parent, service: service || Boolean(node.service) });
        this._nodes[node.id] = entry;
        if (node.kids) index(node.kids, entry, entry.service);
      });
    };
    index(TREE, null, false);
    this._onResize = () => this._fit();
    this._onTouch = () => {
      this._last = Date.now();
    };
    const root = this.shadowRoot;
    root.addEventListener("click", (event) => this._onClick(event));
    root.addEventListener("change", (event) => this._onChange(event));
    root.addEventListener("input", (event) => this._onInput(event));
    root.addEventListener("pointerdown", (event) => this._onPress(event));
    root.addEventListener("pointerup", () => this._stopHold());
    root.addEventListener("pointercancel", () => this._stopHold());
    root.addEventListener("pointerleave", () => this._stopHold());
    root.addEventListener("touchstart", (event) => this._swipeStart(event), { passive: true });
    root.addEventListener("touchend", (event) => this._swipeEnd(event), { passive: true });
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.isConnected) return;
    if (!this._started) this._start();
    else if (this._ready) this._look();
  }

  get hass() {
    return this._hass;
  }

  set embed(value) {
    this._embed = value || null;
    this._fit();
    if (this._ready) this._look();
  }

  get embed() {
    return this._embed;
  }

  home() {
    if (!this._ready) return;
    this._token = null;
    this._goHome();
  }

  set narrow(_value) {}

  set panel(_value) {}

  set route(_value) {}

  connectedCallback() {
    window.addEventListener("resize", this._onResize);
    this.shadowRoot.addEventListener("pointerdown", this._onTouch);
    this._second = setInterval(() => this._tick(), 1000);
    if (this._hass && !this._started) this._start();
    this._fit();
  }

  disconnectedCallback() {
    window.removeEventListener("resize", this._onResize);
    this.shadowRoot.removeEventListener("pointerdown", this._onTouch);
    clearInterval(this._second);
    this._leave();
    this._started = false;
  }

  _leave() {
    if (this._unsubscribe) this._unsubscribe.then((off) => off()).catch(() => {});
    this._unsubscribe = null;
  }

  // text and look

  get _lang() {
    return this._language || "en";
  }

  get _t() {
    return STRINGS[this._lang];
  }

  _state(entity) {
    const state = this._hass && this._hass.states[entity];
    return state ? state.state : null;
  }

  _title(id) {
    const node = this._nodes[id];
    const titles = TITLES[(node && node.title) || id] || [id, id, id];
    return titles[{ ru: 0, lv: 1, en: 2 }[this._lang]];
  }

  _number(value, decimals = 0) {
    if (value === null || value === undefined) return "—";
    return Number(value).toLocaleString(this._t.locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  _unit(unit) {
    return or(this._t.units[unit], or(unit, ""));
  }

  _reading(name, decimals) {
    const item = this._datapoints[name];
    const value = this._dp[name];
    if (value === null || value === undefined) return "—";
    if (item && item.options) return or(item.options[value], String(value));
    if (item && item.flag) return value ? this._t.on : this._t.off;
    const text = this._number(value, or(decimals, item ? item.decimals : 0));
    const unit = this._unit(item ? item.unit : "");
    return unit ? `${text} ${unit}` : text;
  }

  _degrees(value) {
    return value === null || value === undefined ? "—" : `${this._number(value, 1)}°`;
  }

  _setting(item) {
    const value = this._sp[item.name];
    if (value === null || value === undefined) return "—";
    if (item.options) return or(item.options[value], String(value));
    if (item.kind === "switch") return value ? this._t.on : this._t.off;
    const unit = this._unit(item.unit);
    const text = this._number(value, item.decimals);
    return unit ? `${text} ${unit}` : text;
  }

  _problem(err) {
    const texts = this._t.errors;
    const failure = err || {};
    const text = or(texts[failure.code], texts.other);
    return typeof text === "function" ? text(failure.message) : text;
  }

  _look() {
    const app = this.shadowRoot.querySelector(".app");
    if (!app) return;
    const embed = this._embed || {};
    const wanted = embed.language || QUERY.get("lang") || this._state(LANGUAGE_ENTITY) || stored.get("language") || this._hass.language || "en";
    const language = wanted.split("-")[0];
    this._language = STRINGS[language] ? language : "en";
    const chosen = embed.theme || QUERY.get("theme") || this._state(THEME_ENTITY) || stored.get("theme") || "auto";
    const darkHass = this._hass && this._hass.themes && this._hass.themes.darkMode;
    const systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = chosen === "dark" || (chosen !== "light" && (darkHass || systemDark));
    const name = embed.accent || QUERY.get("accent") || this._state(ACCENT_ENTITY) || stored.get("accent") || "blue";
    const accent = ACCENTS[name] || (/^#[0-9a-f]{6}$/i.test(name) ? name : ACCENTS.blue);
    const look = `app ${dark ? "t-dark" : "t-light"}`;
    if (app.className !== look) app.className = look;
    if (this._accent !== accent) {
      this._accent = accent;
      const rgb = [1, 3, 5].map((at) => parseInt(accent.substr(at, 2), 16)).join(",");
      app.style.setProperty("--acc", accent);
      app.style.setProperty("--acc-rgb", rgb);
    }
    if (this._ready && this._loadedLang !== this._lang) this._reload();
  }

  _fit() {
    const app = this.shadowRoot.querySelector(".app");
    if (!app) return;
    if (this._embed) {
      // the host has already scaled the space it gives
      app.style.zoom = 1;
      app.style.width = "100%";
      app.style.height = "100%";
      app.style.marginLeft = "0px";
      return;
    }
    app.style.width = "";
    const box = this.getBoundingClientRect();
    const width = box.width || window.innerWidth;
    const height = box.height || window.innerHeight;
    const zoom = Math.min(3, Math.max(0.4, Math.min(width, height) / BASE));
    app.style.zoom = zoom;
    app.style.height = `${Math.min(height / zoom, BASE * MENU_MAX)}px`;
    app.style.marginLeft = `${Math.max(0, (width / zoom - BASE) / 2)}px`;
  }

  // start

  async _start() {
    this._started = true;
    this._ready = false;
    this._accent = null;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><div class="app t-light"><div id="off"></div><div id="stage" style="position:relative;flex:1;min-height:0"></div></div>`;
    this._look();
    this._fit();
    this._message(STRINGS[this._lang].loading);
    try {
      const info = await this._hass.callWS({ type: `${DOMAIN}/info` });
      this._units = info.units;
      this._admin = info.is_admin;
      if (!this._units.length) {
        this._message(this._t.noUnit);
        return;
      }
      const wanted = (this._embed && this._embed.unit) || QUERY.get("unit") || this._entry;
      const known = this._units.find((unit) => unit.entry_id === wanted);
      this._entry = (known || this._units[0]).entry_id;
      await this._load();
    } catch (err) {
      this._message(err && err.code === "unknown_command" ? this._t.noUnit : this._problem(err));
    }
  }

  async _load() {
    await this._loadSchema();
    this._leave();
    this._unsubscribe = this._hass.connection.subscribeMessage((event) => this._onEvent(event), {
      type: `${DOMAIN}/subscribe`,
      entry_id: this._entry,
    });
    await this._unsubscribe;
  }

  async _loadSchema() {
    const language = this._lang;
    const schema = await this._call("schema", { language });
    this._loadedLang = language;
    this._faultNames = schema.faults;
    const table = (items) => {
      const out = {};
      items.forEach((item) => {
        out[item.name] = item;
      });
      return out;
    };
    this._schema = schema;
    this._datapoints = table(schema.datapoints);
    this._setpoints = table(schema.setpoints);
  }

  async _reload() {
    this._loadedLang = this._lang;
    await this._loadSchema();
    this._draw();
  }

  _call(command, fields = {}) {
    return this._hass.callWS(Object.assign({ type: `${DOMAIN}/${command}`, entry_id: this._entry }, fields));
  }

  _onEvent(event) {
    const first = !this._ready;
    Object.assign(this._dp, event.dp);
    Object.assign(this._sp, event.sp);
    const faults = this._status.faults.length;
    this._status = { available: event.available, virtual: event.virtual, faults: event.faults, words: event.words };
    this._ready = true;
    if (first) this._draw();
    else {
      this._refresh();
      const top = this._top;
      if (top.view === "faults" && faults !== event.faults.length) this._draw();
    }
  }

  _message(text) {
    this.shadowRoot.getElementById("stage").innerHTML = `<div class="center">${esc(text)}</div>`;
  }

  // navigation

  get _top() {
    return this._stack[this._stack.length - 1];
  }

  _go(view, params) {
    this._stack.push(Object.assign({ view }, params));
    this._draw("fwd");
  }

  _back() {
    if (this._stack.length > 1) this._stack.pop();
    this._draw("rev");
  }

  _goHome() {
    this._stack = [{ view: "home" }];
    this._draw("rev");
  }

  _open(id) {
    const node = this._nodes[id];
    if (!node) return;
    if (node.service && !this._token) {
      this._go("pin", { then: id });
    } else if (node.view) {
      this._go(node.view);
    } else if (node.kids) {
      this._go("branch", { id });
    } else {
      this._go("list", { id });
    }
  }

  _homeTarget() {
    const panels = (this._hass && this._hass.panels) || {};
    const shared = this._state(HOME_ENTITY);
    const chosen = QUERY.get("home") || (shared && shared.startsWith("/") ? shared : stored.get("home"));
    return chosen || (panels["nspanel-pro"] ? "/nspanel-pro/home" : "/");
  }

  _panelTitle(panel) {
    const translated = this._hass.localize ? this._hass.localize(`panel.${panel.title}`) : "";
    return translated || panel.title;
  }

  _homeName() {
    const path = this._homeTarget();
    const panel = (this._hass.panels || {})[path.split("/")[1]];
    if (panel && panel.title) return this._panelTitle(panel);
    return path === "/" ? "Home Assistant" : path;
  }

  _exit() {
    if (this._embed) {
      this.dispatchEvent(new CustomEvent("alpicair-nest-leave", { bubbles: true, composed: true }));
      return;
    }
    history.pushState(null, "", this._homeTarget());
    window.dispatchEvent(new CustomEvent("location-changed", { bubbles: true, composed: true }));
  }

  _draw(motion) {
    const stage = this.shadowRoot.getElementById("stage");
    if (!stage || !this._ready) return;
    const top = this._top;
    const screen = document.createElement("section");
    screen.className = `screen ${motion || ""}`;
    screen.innerHTML = this[`_view_${top.view}`](top);
    stage.innerHTML = "";
    stage.appendChild(screen);
    if (top.view === "week" || top.view === "day") this._ensureSchedule();
    if (top.view === "history") this._loadHistory();
    if (top.view === "targets") this._loadTargets();
    this._refresh();
  }

  _bar(title, sub = "", home = true) {
    return `<div class="bar">
      <button class="tap" data-do="back" aria-label="back">${icon("back")}</button>
      <div class="bar-text"><b>${esc(title)}</b><span>${esc(sub)}</span></div>
      ${home ? `<button class="tap" data-do="home" aria-label="home">${icon("home")}</button>` : ""}
    </div>`;
  }

  _crumb(id) {
    const node = this._nodes[id];
    return node && node.parent ? this._title(node.parent.id) : this._t.menu;
  }

  // live values

  _refresh() {
    const root = this.shadowRoot;
    const set = (node, text) => {
      if (node.textContent !== text) node.textContent = text;
    };
    const bar = root.getElementById("off");
    const offline = !this._status.available;
    if (bar.hidden !== !offline || !bar.dataset.ready) {
      bar.dataset.ready = "1";
      bar.hidden = !offline;
      bar.className = offline ? "off-bar" : "";
      bar.textContent = offline ? this._t.offline : "";
    }
    root.querySelectorAll("[data-dp]").forEach((node) => {
      const name = node.dataset.dp;
      const item = this._datapoints[name];
      if (item && item.flag) {
        const on = Boolean(this._dp[name]);
        node.innerHTML = `<i class="lamp ${on ? "on" : ""}"></i>${esc(on ? this._t.on : this._t.off)}`;
      } else set(node, this._reading(name));
    });
    root.querySelectorAll("[data-deg]").forEach((node) => set(node, this._degrees(this._dp[node.dataset.deg])));
    root.querySelectorAll("[data-deg0]").forEach((node) => {
      const value = this._dp[node.dataset.deg0];
      set(node, value === null || value === undefined ? "—" : `${this._number(value, 0).replace("-", "−")}°`);
    });
    root.querySelectorAll("[data-set]").forEach((node) => {
      const item = this._setpoints[node.dataset.set];
      if (item) set(node, this._setting(item));
    });
    root.querySelectorAll("[data-switch]").forEach((node) => {
      if (!node.dataset.busy) node.checked = Boolean(this._sp[node.dataset.switch]);
    });
    root.querySelectorAll("[data-live]").forEach((node) => set(node, this._live(node.dataset.live)));
    const view = this._top.view;
    if (view === "home") this._refreshHome();
    if (view === "temp") this._refreshTemp();
    if (view === "modes") this._refreshModes();
    if (view === "editor") this._showValue();
    if (view === "branch" && this._nodes[this._top.id].service) this._tick();
  }

  _modeState() {
    const t = this._t;
    const mode = this._dp.CurrentOperatingMode;
    const how = { 0: t.onSchedule, 1: t.manual, 2: t.temporary }[this._sp.ControlMode];
    return { mode: or(t.modes[mode], "—"), how: how || "" };
  }

  _airValue() {
    const t = this._t;
    const inputs = [this._sp.AI1_Configuration, this._sp.AI2_Configuration, this._sp.AI3_Configuration];
    if (inputs.includes(1)) return [t.humidity, this._reading("AI_ExtractAirHumidity")];
    if (inputs.includes(3)) return [t.humidity, this._reading("AI_SupplyAirHumidity")];
    if (inputs.includes(2)) return ["CO₂", this._reading("AI_ExtractAirCO2")];
    const efficiency = this._status.virtual.recovery_efficiency;
    return [t.recovery, efficiency === undefined ? "—" : `${this._number(efficiency)} %`];
  }

  _live(key) {
    const t = this._t;
    switch (key) {
      case "mode": return this._modeState().mode;
      case "climate": return this._degrees(this._targetValue());
      case "vent": return this._reading("Fan1_Output", 0);
      case "air": return this._airValue()[1];
      case "schedule": return this._modeState().how;
      case "readings": return this._degrees(this._dp.T_Outdoor);
      case "faults": return this._status.faults.length ? String(this._status.faults.length) : t.noFaults;
      case "system": return `${t.filter}: ${this._reading("Filter_RemainingDays")}`;
      case "service": return this._token ? this._t.open(this._left()) : "PIN";
      case "clock": return this._deviceClock();
      default: return "";
    }
  }

  _deviceClock() {
    const { Date: date, Month, Year, Hour, Min } = this._sp;
    if (Hour === undefined || date === undefined) return "—";
    return `${two(date)}.${two(Month)}.20${two(Year)}  ${two(Hour)}:${two(Min)}`;
  }

  // home

  get _layout() {
    const chosen = (this._embed && this._embed.layout) || QUERY.get("layout") || stored.get("layout");
    return LAYOUTS.indexOf(chosen) >= 0 ? chosen : "house";
  }

  _view_home(top) {
    return this._layout === "fan" ? this._view_fanhome() : this._view_house(top);
  }

  _view_house(top) {
    const t = this._t;
    const sheet = { mode: () => this._sheetMode(), temp: () => this._sheetTemp(), fan: () => this._sheetFan() }[top.sheet];
    const label = (left, topPx, name) => `<div class="hl" style="left:${left}px;top:${topPx}px" data-deg0="${name}"></div>`;
    return `<div class="home">
      <div class="house-wrap"><div class="house">
        <svg viewBox="0 0 460 352" aria-hidden="true">
          <rect x="292" y="74" width="28" height="70" rx="3" fill="var(--roof)"/>
          <rect x="288" y="70" width="36" height="10" rx="3" fill="var(--roof)"/>
          <polygon points="96,172 230,74 364,172" fill="var(--attic)"/>
          <rect x="96" y="166" width="268" height="173" rx="3" fill="var(--wall)" stroke="var(--line)" stroke-width="2"/>
          <path d="M96 172 H364" stroke="var(--line)" stroke-width="2"/>
          <polygon points="192,114 268,114 284,137 268,160 192,160 176,137" fill="var(--wall)"/>
          <path d="M282.7 114.7 L276 121 L184 121 L160 141 M296.7 128.1 L284 139 L190 139 L166 161" stroke="#38bdf8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M172 118.6 L182 130 L278 130 L300 152 M160 129.4 L176 148 L284 148 L297.3 160.7" stroke="#f97316" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <polygon points="192,114 268,114 284,137 268,160 192,160 176,137" fill="none" stroke="var(--tx)" stroke-width="3" stroke-linejoin="round"/>
          <path d="M70 180 L230 60 L390 180" stroke="var(--roof)" stroke-width="16" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M128 118 L78 80 M96.8 81.7 L78 80 L84.7 97.7" stroke="#f97316" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M412 72 L322 114 M340.7 116.3 L322 114 L332.3 98.1" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M128 182 V236 M117 224 L128 237 L139 224" stroke="#38bdf8" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M332 237 V183 M321 196 L332 183 L343 196" stroke="#f97316" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <path d="M24 339 H436" stroke="var(--ground)" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <div class="clock" id="h-time"></div>
        ${this._embed ? `<button class="tap" data-do="exit" aria-label="${esc(t.exit)}">${icon("back")}</button>` : ""}
        <button class="badge" id="h-faults" data-node="faults" hidden></button>
        ${label(6, 26, "T_Exhaust")}${label(330, 20, "T_Outdoor")}${label(88, 246, "T_Supply")}${label(292, 246, "T_Extract")}
        <div class="house-mid">
          <button class="house-speed" data-do="sheet" data-sheet="fan" aria-label="${esc(t.fanSpeed)}"><b id="h-speed"></b><small id="h-speed-unit"></small></button>
          <button class="house-mode" data-do="sheet" data-sheet="mode">${icon("power")}<span id="h-mode"></span></button>
        </div>
      </div></div>
      <div class="dock tall">
        <button data-do="sheet" data-sheet="temp">${icon("thermo")}<b id="h-dock-temp"></b><span>${esc(t.temperature)}</span></button>
        <button data-do="air">${icon("drop")}<b id="h-dock-air"></b><span id="h-dock-air-label"></span></button>
        <button class="accent" data-do="menu">${icon("grid")}<b>${esc(t.menu)}</b></button>
      </div>
      ${sheet ? `<div class="sheet-shade" data-do="sheet-close"><div class="sheet" data-do="noop">${sheet()}</div></div>` : ""}
    </div>`;
  }

  _sheetMode() {
    const t = this._t;
    const auto = this._sp.ControlMode === 0;
    const current = this._dp.CurrentOperatingMode;
    const pick = (mode, label, cls = "") => `<button class="pick ${cls} ${!auto && mode === current ? "on" : ""}" data-mode="${mode}">
      <b>${esc(label)}</b><span>${esc(mode ? this._modeFacts(mode) : "")}</span></button>`;
    return `<div class="sheet-head"><b>${esc(t.mode)}</b><span>${esc(t.closesOnPick)}</span></div>
      <div class="picks">
        <button class="pick span ${auto ? "on" : ""}" data-do="auto"><b>${esc(t.scheduleMode)}</b><span>${esc(auto ? this._modeState().mode : "")}</span></button>
        ${[1, 2, 3, 4, 5].map((mode) => pick(mode, t.modes[mode])).join("")}${pick(0, t.turnOff)}
      </div>`;
  }

  _sheetTemp() {
    const t = this._t;
    return `<div class="sheet-head"><b>${esc(t.temperature)} · ${esc(this._modeState().mode)}</b><span>${esc(t.tapOutside)}</span></div>
      <div class="sheet-row">
        <button class="sheet-step" data-do="target" data-step="-1" aria-label="−">${icon("minus")}</button>
        <div class="sheet-mid">${this._ring("small", `<b id="r-value"></b><span id="r-note"></span>`)}</div>
        <button class="sheet-step" data-do="target" data-step="1" aria-label="+">${icon("plus")}</button>
      </div>`;
  }

  _sheetFan() {
    const t = this._t;
    return `<div class="sheet-head"><b>${esc(t.fanSpeed)} · ${esc(this._modeState().mode)}</b><span>${esc(t.tapOutside)}</span></div>
      <div class="sheet-row">
        <button class="sheet-step low" data-fan="-1" aria-label="−">${icon("minus")}</button>
        <div class="sheet-mid"><b id="s-speed"></b><div class="bar-line"><i id="s-bar"></i></div></div>
        <button class="sheet-step low" data-fan="1" aria-label="+">${icon("plus")}</button>
      </div>`;
  }

  _openSheet(kind) {
    this._top.sheet = kind;
    this._draw();
  }

  _closeSheet() {
    if (!this._top.sheet) return;
    this._top.sheet = null;
    this._draw();
  }

  // what the fans are asked to do in this mode, while tapping too
  _fanAsked() {
    const items = this._fanItems();
    const now = this._fanNow();
    const item = items ? items[0] : { min: 0, max: 100 };
    const pending = items && this._pendingFan && this._pendingFan.items[0].name === item.name ? this._pendingFan : null;
    const asked = items ? (pending ? pending.values[0] : this._sp[item.name]) : now.value;
    return { items, now, item, asked };
  }

  _refreshHouse() {
    const root = this.shadowRoot;
    const { items, now, item, asked } = this._fanAsked();
    this._put("h-mode", this._modeState().mode);
    this._put("h-time", this._clock());
    this._put("h-speed", this._number(asked));
    this._put("h-speed-unit", now.unit);
    this._put("h-dock-temp", this._degrees(this._targetValue()));
    const air = this._airValue();
    this._put("h-dock-air", air[1]);
    this._put("h-dock-air-label", air[0]);
    this._refreshBadge();
    const sheet = this._top.sheet;
    if (sheet === "temp") this._refreshTemp();
    if (sheet === "fan") {
      const speed = root.getElementById("s-speed");
      speed.innerHTML = `${esc(this._number(asked))}<small>${esc(now.unit)}</small>`;
      const share = item.max > item.min ? (or(asked, item.min) - item.min) / (item.max - item.min) : 0;
      root.getElementById("s-bar").style.width = `${Math.round(Math.min(1, Math.max(0, share)) * 100)}%`;
      root.querySelectorAll("[data-fan]").forEach((button) => {
        button.disabled = !items;
      });
    }
  }

  _refreshBadge() {
    const badge = this.shadowRoot.getElementById("h-faults");
    const faults = this._status.faults;
    badge.hidden = !faults.length;
    badge.style.display = faults.length ? "" : "none";
    if (faults.length) {
      badge.className = `badge ${faults.some((fault) => fault.kind === "error") ? "" : "warn"}`;
      badge.innerHTML = `${icon("alert")}${faults.length}`;
    }
  }

  _view_fanhome() {
    const t = this._t;
    const side = (id, label, step, glyph) => `<div class="fan-side">
        <div class="fan-who"><span>${esc(label)}</span><b id="h-${id}"></b><small id="h-${id}-rpm"></small></div>
        <button class="fan-step" data-fan="${step}" aria-label="${step < 0 ? "−" : "+"}">${icon(glyph)}</button>
      </div>`;
    const cell = (kind, label, name) => `<div class="temp-cell"><span><i class="${kind}"></i>${esc(label)}</span><b data-deg="${name}"></b></div>`;
    return `<div class="home">
      <div class="top">
        ${this._embed ? `<button class="tap" data-do="exit" aria-label="${esc(t.exit)}">${icon("back")}</button>` : ""}
        <div class="state"><b id="h-mode"></b><span id="h-how"></span></div>
        <button class="badge" id="h-faults" data-node="faults" hidden></button>
        <div class="time" id="h-time"></div>
      </div>
      <div class="fan-card">
        ${side("supply", t.supply, -1, "minus")}
        <button class="ring-tap" data-node="mode">${this._ring("", `<span class="fan-wrap" id="h-fan">${icon("fan")}</span><b id="r-value"></b><span class="ring-mode" id="r-note"></span>`)}</button>
        ${side("extract", t.extract, 1, "plus")}
      </div>
      <button class="temps" data-do="flow">
        ${cell("fresh", t.outdoor, "T_Outdoor")}
        ${cell("fresh", t.toRooms, "T_Supply")}
        ${cell("stale", t.fromRooms, "T_Extract")}
        ${cell("stale", t.exhaust, "T_Exhaust")}
      </button>
      <div class="dock">
        <button data-node="mode">${icon("power")}<b id="h-dock-mode"></b><span>${esc(t.mode)}</span></button>
        <button data-do="temp">${icon("thermo")}<b id="h-dock-temp"></b><span>${esc(t.temperature)}</span></button>
        <button data-do="air">${icon("drop")}<b id="h-dock-air"></b><span id="h-dock-air-label"></span></button>
        <button class="accent" data-do="menu">${icon("grid")}<b>${esc(t.menu)}</b></button>
      </div>
    </div>`;
  }

  _ring(cls, text) {
    const C = 2 * Math.PI * 82;
    this._arc = C * 0.75;
    return `<div class="ring ${cls}">
      <svg viewBox="0 0 200 200" aria-hidden="true">
        <circle class="ring-track" cx="100" cy="100" r="82" transform="rotate(135 100 100)" stroke-dasharray="${this._arc.toFixed(1)} ${C.toFixed(1)}"/>
        <circle class="ring-value" id="r-arc" cx="100" cy="100" r="82" transform="rotate(135 100 100)" stroke-dasharray="0 ${C.toFixed(1)}"/>
        <circle class="ring-dot" id="r-dot" r="7" cx="100" cy="18"/>
      </svg>
      <div class="ring-text">${text}</div>
    </div>`;
  }

  // the arc shows what is asked for, the dot what is happening; both as shares of the range
  _showRing(share, place) {
    const root = this.shadowRoot;
    const circle = 2 * Math.PI * 82;
    const part = (value) => (value === null || value === undefined || Number.isNaN(value) ? 0 : Math.min(1, Math.max(0, value)));
    root.getElementById("r-arc").setAttribute("stroke-dasharray", `${(this._arc * part(share)).toFixed(1)} ${circle.toFixed(1)}`);
    const angle = ((135 + 270 * part(place)) * Math.PI) / 180;
    const dot = root.getElementById("r-dot");
    dot.setAttribute("cx", (100 + 82 * Math.cos(angle)).toFixed(1));
    dot.setAttribute("cy", (100 + 82 * Math.sin(angle)).toFixed(1));
  }

  _put(id, text) {
    const node = this.shadowRoot.getElementById(id);
    if (node.textContent !== text) node.textContent = text;
  }

  // the fans

  _fanName(mode, fan) {
    const strategy = this._sp.Fans_ControlStrategy;
    const suffix = { 1: "Unoccupied", 2: "Economy", 3: "Comfort", 4: "Boost", 5: "KitchenHood" }[mode];
    const start = { 0: `Linear_Fan${fan}_Fanspeed_`, 1: `Constant_Airflow_Fan${fan}_`, 2: `Constant_Pressure_Fan${fan}_` }[strategy];
    if (!suffix || !start) return null;
    return start + (strategy === 0 ? suffix.replace("Hood", "hood") : suffix);
  }

  // the two settings behind the current mode; none when off, or when the fans follow an outside signal
  _fanItems() {
    const mode = this._dp.CurrentOperatingMode;
    const items = [1, 2].map((fan) => this._setpoints[this._fanName(mode, fan)]);
    return items[0] && items[1] ? items : null;
  }

  _fanNow() {
    const name = { 1: "Airflow_Supply", 2: "Pressure_1" }[this._sp.Fans_ControlStrategy] || "Fan1_Output";
    return { value: this._dp[name], unit: this._unit(this._datapoints[name] ? this._datapoints[name].unit : "%") };
  }

  _refreshFan() {
    const { items, now, item, asked } = this._fanAsked();
    const range = item.max - item.min;
    this._showRing((asked - item.min) / range, (or(now.value, item.min) - item.min) / range);
    const value = this.shadowRoot.getElementById("r-value");
    value.innerHTML = `${esc(this._number(asked))}<small>${esc(now.unit)}</small>`;
    value.className = now.unit === "%" ? "" : "tight";
    this._put("r-note", this._modeState().mode);
    this._put("h-supply", this._reading("Fan1_Output", 0));
    this._put("h-extract", this._reading("Fan2_Output", 0));
    this._put("h-supply-rpm", this._reading("Fan1_RPM"));
    this._put("h-extract-rpm", this._reading("Fan2_RPM"));
    this.shadowRoot.querySelectorAll("[data-fan]").forEach((button) => {
      button.disabled = !items;
    });
    const fan = this.shadowRoot.getElementById("h-fan");
    const output = or(this._dp.Fan1_Output, 0);
    fan.classList.toggle("spin", output > 0);
    fan.style.setProperty("--speed", `${Math.max(0.5, 3.2 - output / 40).toFixed(1)}s`);
  }

  _nudgeFan(direction) {
    const items = this._fanItems();
    if (!items) return;
    if (!this._canChange(items[0])) {
      this._toast(this._t.adminOnly);
      return;
    }
    const pending = this._pendingFan;
    const same = pending && pending.items[0].name === items[0].name;
    const values = same ? pending.values : items.map((item) => or(this._sp[item.name], item.min));
    // both move by the same amount, so the balance between supply and extract stays as it was
    let change = direction * FAN_STEPS[this._sp.Fans_ControlStrategy];
    items.forEach((item, index) => {
      change = Math.min(item.max - values[index], Math.max(item.min - values[index], change));
    });
    if (!change && !same) return;
    this._pendingFan = { items, values: values.map((value) => value + change) };
    this._refreshHome();
    clearTimeout(this._fanTimer);
    // like the temperature, these live in EEPROM: one write when the tapping stops
    this._fanTimer = setTimeout(() => this._saveFan(), SAVE_PAUSE);
  }

  async _saveFan() {
    const pending = this._pendingFan;
    try {
      for (let index = 0; index < pending.items.length; index += 1) {
        const name = pending.items[index].name;
        const result = await this._call("write", { name, value: pending.values[index] });
        this._sp[name] = result.value;
      }
    } catch (err) {
      this._toast(this._problem(err));
    }
    if (this._pendingFan === pending) this._pendingFan = null;
    this._refresh();
  }

  // temperature

  _view_temp() {
    const t = this._t;
    return `${this._bar(t.temperature, this._modeState().mode)}
      <div class="body"><div class="ring-card">
        ${this._ring("large", `<b id="r-value"></b><span id="r-note"></span>`)}
        <div class="ring-buttons">
          <button data-do="target" data-step="-1" aria-label="−">${icon("minus")}</button>
          <button data-do="target" data-step="1" aria-label="+">${icon("plus")}</button>
        </div>
      </div></div>`;
  }

  _targetName() {
    const side = this._sp.AirTemp_ControlStrategy === 1 ? "Extract" : "Supply";
    const mode = or({ 1: "Unoccupied", 2: "Economy", 3: "Comfort" }[this._dp.CurrentOperatingMode], "Comfort");
    return `AirTemp_${side}Target_${mode}`;
  }

  _targetLimits() {
    const item = this._setpoints[this._targetName()] || { min: 0, max: 50 };
    return {
      low: Math.max(item.min, or(this._sp.AirTemp_MinAllowedSetpoint, item.min)),
      high: Math.min(item.max, or(this._sp.AirTemp_MaxAllowedSetpoint, item.max)),
    };
  }

  _targetValue() {
    const raw = this._pendingTarget ? this._pendingTarget.value : this._sp[this._targetName()];
    if (raw === undefined || raw === null) return null;
    const { low, high } = this._targetLimits();
    return Math.min(high, Math.max(low, raw));
  }

  _refreshTemp() {
    const t = this._t;
    const value = this._targetValue();
    const { low, high } = this._targetLimits();
    const extract = this._sp.AirTemp_ControlStrategy === 1;
    const current = this._dp[extract ? "T_Extract" : "T_Supply"];
    const range = high - low;
    this._showRing(value === null ? 0 : (value - low) / range, (or(current, low) - low) / range);
    this.shadowRoot.getElementById("r-value").innerHTML = value === null ? "—" : `${this._number(value, 1)}<small>°C</small>`;
    this._put("r-note", `${extract ? t.extract : t.supply} ${this._degrees(current)}`);
  }

  _refreshHome() {
    if (this._layout !== "fan") {
      this._refreshHouse();
      return;
    }
    const t = this._t;
    const { mode, how } = this._modeState();
    const phase = t.phases[this._dp.AirTemp_PhaseControl_WhatPhase];
    const running = this._dp.CurrentOperatingMode !== 0;
    this._put("h-mode", mode);
    this._put("h-how", [how, running ? phase : ""].filter(Boolean).join(" · "));
    this._put("h-time", this._clock());
    this._refreshFan();
    this._put("h-dock-mode", mode);
    this._put("h-dock-temp", this._degrees(this._targetValue()));
    const air = this._airValue();
    this._put("h-dock-air", air[1]);
    this._put("h-dock-air-label", air[0]);
    this._refreshBadge();
  }

  _clock() {
    const now = new Date();
    return `${two(now.getHours())}:${two(now.getMinutes())}`;
  }

  _nudgeTarget(direction) {
    const name = this._targetName();
    const start = this._pendingTarget && this._pendingTarget.name === name ? this._pendingTarget.value : this._targetValue();
    if (start === null) return;
    const { low, high } = this._targetLimits();
    this._pendingTarget = { name, value: Math.min(high, Math.max(low, start + direction * TARGET_STEP)) };
    if (this._top.view === "home") this._refreshHome();
    else this._refreshTemp();
    clearTimeout(this._targetTimer);
    // the value lives in EEPROM: one write when the tapping stops, not one per tap
    this._targetTimer = setTimeout(async () => {
      const pending = this._pendingTarget;
      try {
        const result = await this._call("write", { name: pending.name, value: pending.value });
        this._sp[pending.name] = result.value;
      } catch (err) {
        this._toast(this._problem(err));
      }
      this._pendingTarget = null;
      this._refresh();
    }, SAVE_PAUSE);
  }

  // main menu and submenus

  _view_menu() {
    const t = this._t;
    const tile = (node) => {
      const count = node.id === "faults" && this._status.faults.length;
      return `<button class="tile" data-node="${node.id}">
        <div class="box">${icon(node.icon)}</div>
        ${count ? `<div class="count">${count}</div>` : ""}
        <div><b>${esc(this._title(node.id))}</b><span data-live="${node.id}"></span></div>
      </button>`;
    };
    return `<div class="bar">
        <button class="tap" data-do="home" aria-label="home">${icon("home")}</button>
        <div class="bar-text"><b>${esc(t.menu)}</b></div>
      </div>
      <div class="body">
        <div class="grid short">${TREE.map(tile).join("")}</div>
        <div class="leave">
          <button class="out" data-do="exit" aria-label="${esc(t.exit)}">${icon("exit")}<b>${esc(this._embed ? this._embed.leave || t.exit : this._homeName())}</b></button>
          ${this._embed ? "" : `<button class="set" data-do="targets" aria-label="${esc(t.menuButton)}">${icon("sliders")}</button>`}
        </div>
      </div>`;
  }

  _items(node) {
    const service = node.service;
    return this._schema.setpoints.filter(
      (item) => node.match.test(item.name) && (item.level === "service") === service && item.name !== "Scheduler_Mode"
    );
  }

  _size(node) {
    if (node.kids) return this._t.sections(node.kids.length);
    if (node.match) return this._t.settings(this._items(node).length);
    return "";
  }

  _view_branch(top) {
    const t = this._t;
    const node = this._nodes[top.id];
    const rows = node.kids
      .map((kid) => {
        const entry = this._nodes[kid.id];
        return `<button class="row" data-node="${kid.id}"><div class="box">${icon(kid.icon)}</div>
          <div class="row-text"><b>${esc(this._title(kid.id))}</b><span>${esc(this._size(entry))}</span></div>${icon("chevron", "go")}</button>`;
      })
      .join("");
    const lock = node.id === "service" ? `<button class="wide soft" data-do="lock">${icon("lock")}${esc(t.lock)}</button>` : "";
    const sub = node.id === "service" ? `<span id="service-left"></span>` : esc(this._crumb(top.id));
    return `<div class="bar"><button class="tap" data-do="back" aria-label="back">${icon("back")}</button>
        <div class="bar-text"><b>${esc(this._title(top.id))}</b><span>${sub}</span></div>
        <button class="tap" data-do="home" aria-label="home">${icon("home")}</button></div>
      <div class="body"><div class="group">${rows}</div>${lock}</div>`;
  }

  _canChange(item) {
    if (item.level === "user") return true;
    if (item.level === "adjuster") return Boolean(this._admin);
    return Boolean(this._token);
  }

  _row(item) {
    const editable = this._canChange(item);
    const name = esc(item.name);
    const meta = item.level === "adjuster" && !editable ? `<span>${esc(this._t.adminOnly)}</span>` : "";
    const text = `<div class="row-text"><b>${esc(item.label)}</b>${meta}</div>`;
    if (item.read_only) return `<div class="row">${text}<div class="row-value" data-set="${name}"></div></div>`;
    switch (item.kind) {
      case "button":
        return `<div class="row">${text}<button class="pill ${item.danger ? "danger" : ""}" data-press="${name}" ${editable ? "" : "disabled"}>${esc(this._t.run)}</button></div>`;
      case "switch":
        return `<div class="row">${text}<label class="toggle"><input type="checkbox" data-switch="${name}" ${editable ? "" : "disabled"}><i></i></label></div>`;
      default:
        return `<button class="row" data-edit="${name}" ${editable ? "" : "disabled"}>${text}<div class="row-value" data-set="${name}"></div>${icon("chevron", "go")}</button>`;
    }
  }

  _view_list(top) {
    const node = this._nodes[top.id];
    const extra =
      node.clock
        ? `<div class="group"><div class="row"><div class="row-text"><b>${esc(this._t.clock)}</b><span data-live="clock"></span></div></div></div>
           <button class="wide" data-do="sync">${icon("clock")}${esc(this._t.syncClock)}</button>`
        : "";
    return `${this._bar(this._title(top.id), this._crumb(top.id))}
      <div class="body">${extra}<div class="group">${this._items(node).map((item) => this._row(item)).join("")}</div></div>`;
  }

  // modes

  _view_modes() {
    const t = this._t;
    const card = (mode, name, cls = "") => `<button class="mode ${cls}" data-mode="${mode}">
      <div class="box">${icon(name)}</div><div><b>${esc(t.modes[mode])}</b><span id="m-${mode}"></span></div></button>`;
    return `${this._bar(this._title("mode"), t.menu)}
      <div class="body"><div class="modes">
        <button class="mode span" data-do="auto"><div class="box">${icon("calendar")}</div>
          <div><b>${esc(t.scheduleMode)}</b><span id="m-auto"></span></div></button>
        ${card(1, "moon")}${card(2, "leaf")}${card(3, "person")}${card(4, "rocket")}${card(5, "hood")}
        <button class="mode" data-mode="0"><div class="box">${icon("power")}</div><div><b>${esc(t.turnOff)}</b></div></button>
      </div></div>`;
  }

  _modeFacts(mode) {
    const suffix = { 1: "Unoccupied", 2: "Economy", 3: "Comfort" }[mode];
    const fan = this._setpoints[this._fanName(mode, 1)];
    const speed = fan ? this._setting(fan) : "";
    const side = this._sp.AirTemp_ControlStrategy === 1 ? "Extract" : "Supply";
    const target = mode <= 3 ? this._degrees(this._sp[`AirTemp_${side}Target_${suffix}`]) : "";
    const timer = mode === 4 && this._sp.BoostMode_Timer ? `${this._number(this._sp.BoostMode_Timer)} ${this._unit("min")}` : "";
    return [speed, target, timer].filter(Boolean).join(" · ");
  }

  _refreshModes() {
    const root = this.shadowRoot;
    const auto = this._sp.ControlMode === 0;
    const current = this._dp.CurrentOperatingMode;
    root.querySelector('[data-do="auto"]').classList.toggle("on", auto);
    root.querySelectorAll("[data-mode]").forEach((node) => {
      const mode = Number(node.dataset.mode);
      node.classList.toggle("on", !auto && mode === current);
      const label = root.getElementById(`m-${mode}`);
      if (label) label.textContent = this._modeFacts(mode);
    });
    root.getElementById("m-auto").textContent = auto ? this._modeState().mode : "";
  }

  // editor for numbers, picker for choices

  _view_editor(top) {
    const t = this._t;
    const item = this._setpoints[top.name];
    if (top.value === undefined) top.value = or(this._sp[top.name], item.min);
    const step = this._stepOf(item);
    const slide = (item.max - item.min) / step <= 3000;
    const unit = this._unit(item.unit);
    if (top.typing) {
      const keys = ["1", "2", "3", "⌫", "4", "5", "6", item.decimals ? "," : "", "7", "8", "9", item.min < 0 ? "-" : ""];
      const key = (name) => (name ? `<button data-key="${name}">${name === "⌫" ? icon("erase") : name === "-" ? "−" : esc(name)}</button>` : "<span></span>");
      return `${this._bar(item.label, t.range(this._number(item.min, item.decimals), this._number(item.max, item.decimals)), false)}
        <div class="body"><div class="editor">
          <div class="big"><b id="ed-value">${esc(top.text || "0")}</b><small>${esc(unit)}</small></div>
          <div class="grow"></div>
          <div class="keys four">${keys.map(key).join("")}<button class="all" data-key="0">0</button></div>
          <div class="foot"><button data-do="keys-off">${esc(t.cancel)}</button><button class="main" data-do="keys-ok">${esc(t.ok)}</button></div>
        </div></div>`;
    }
    return `${this._bar(item.label, this._crumbOf(top), false)}
      <div class="body"><div class="editor">
        <div class="big"><button data-do="keys-on"><b id="ed-value"></b><small>${esc(unit)}</small></button></div>
        <div class="limits">${esc(t.range(this._number(item.min, item.decimals), this._number(item.max, item.decimals)))} · ${esc(t.factory)} ${esc(this._number(item.default, item.decimals))}</div>
        ${slide ? `<div class="slider"><input type="range" id="ed-slider" min="${item.min}" max="${item.max}" step="${step}" value="${top.value}" aria-label="${esc(item.label)}"></div>` : `<div class="grow"></div>`}
        <div class="grow"></div>
        <div class="steps">
          <button data-hold="-1" aria-label="−">${icon("minus")}</button>
          <button data-hold="1" aria-label="+">${icon("plus")}</button>
        </div>
        <div class="foot"><button data-do="back">${esc(t.cancel)}</button><button class="main" data-do="save">${esc(t.save)}</button></div>
      </div></div>`;
  }

  _crumbOf(top) {
    const below = this._stack[this._stack.length - 2];
    return below && below.id ? this._title(below.id) : "";
  }

  _stepOf(item) {
    if (item.unit === "°C" && item.decimals <= 1) return TARGET_STEP;
    return item.decimals ? 10 ** -item.decimals : 1;
  }

  _showValue() {
    const top = this._top;
    const item = this._setpoints[top.name];
    const value = this.shadowRoot.getElementById("ed-value");
    if (value && !top.typing) value.textContent = this._number(top.value, item.decimals);
    const slider = this.shadowRoot.getElementById("ed-slider");
    if (slider) slider.value = top.value;
  }

  _stepValue(direction, factor) {
    const top = this._top;
    const item = this._setpoints[top.name];
    const step = this._stepOf(item) * factor;
    top.value = Math.min(item.max, Math.max(item.min, Number((top.value + direction * step).toFixed(item.decimals))));
    this._showValue();
  }

  async _saveEditor() {
    const top = this._top;
    const item = this._setpoints[top.name];
    if (await this._write(item, top.value)) this._back();
  }

  async _write(item, value) {
    const t = this._t;
    if (item.danger && !(await this._ask(`${item.label}: ${this._number(value, item.decimals)}`, t.dangerSet))) return false;
    const fields = { name: item.name, value };
    if (item.level === "service") fields.token = this._token;
    if (item.danger) fields.confirm = true;
    try {
      const result = await this._call("write", fields);
      this._sp[item.name] = result.value;
      this._toast(t.saved);
      return true;
    } catch (err) {
      this._failed(err);
      return false;
    }
  }

  _failed(err) {
    this._toast(this._problem(err));
    if (err && err.code === "service_locked") this._lock();
  }

  _view_options(top) {
    const item = this._setpoints[top.name];
    const current = this._sp[top.name];
    const rows = Object.keys(item.options)
      .map((value) => {
        const on = String(current) === value;
        return `<button class="row" data-pick="${esc(value)}"><div class="row-text"><b>${esc(item.options[value])}</b></div>${on ? icon("check") : ""}</button>`;
      })
      .join("");
    return `${this._bar(item.label, this._crumbOf(top), false)}<div class="body"><div class="group">${rows}</div></div>`;
  }

  // schedule

  async _ensureSchedule() {
    if (this._days) return;
    try {
      const result = await this._call("schedule");
      this._days = result.days;
      this._draw();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _activeEvents(day) {
    return this._days[day].filter((event) => event[2] > 0).map((event) => event.slice());
  }

  _segments(day) {
    const events = this._activeEvents(day).sort((a, b) => minutes(a) - minutes(b));
    let before = null;
    for (let back = 1; back < DAYS && !before; back += 1) {
      before = this._activeEvents((day + DAYS - back) % DAYS).sort((a, b) => minutes(a) - minutes(b)).pop() || null;
    }
    const parts = [];
    if (before && (!events.length || minutes(events[0]) > 0)) parts.push([0, events.length ? minutes(events[0]) : 1440, before[2]]);
    events.forEach((event, index) => {
      parts.push([minutes(event), index + 1 < events.length ? minutes(events[index + 1]) : 1440, event[2]]);
    });
    return parts;
  }

  _view_week() {
    const t = this._t;
    if (!this._days) return `${this._bar(this._title("schedule"), t.menu)}<div class="center">${esc(t.loading)}</div>`;
    const rows = t.daysShort.map((name, day) => {
      const parts = this._segments(day)
        .map((part) => `<i class="m${part[2]}" style="left:${(part[0] / 14.4).toFixed(2)}%;width:${((part[1] - part[0]) / 14.4).toFixed(2)}%"></i>`)
        .join("");
      return `<button class="day" data-day="${day}"><b>${esc(name)}</b><div class="line">${parts}</div></button>`;
    });
    const legend = [1, 2, 3, 4, 5].map((mode) => `<span><i class="m${mode}"></i>${esc(t.scheduleModes[mode])}</span>`).join("");
    const banner =
      this._sp.ControlMode !== 0
        ? `<div class="note">${esc(t.notRunning)}</div><button class="wide" data-do="auto">${esc(t.turnOn)}</button>`
        : "";
    const scheduler = this._setpoints.Scheduler_Mode;
    return `${this._bar(this._title("schedule"), t.week)}
      <div class="body">${banner}
        <div class="group" style="padding-top:6px">${rows.join("")}
          <div class="scale"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div>
          <div class="legend">${legend}</div></div>
        ${scheduler ? `<div class="group">${this._row(scheduler)}</div>` : ""}
      </div>`;
  }

  _openDay(day) {
    this._go("day", { day, events: this._activeEvents(day) });
  }

  _view_day(top) {
    const t = this._t;
    const sorted = top.events.map((event, index) => ({ event, index })).sort((a, b) => minutes(a.event) - minutes(b.event));
    const rows = sorted
      .map(
        ({ event, index }) => `<button class="row" data-event="${index}">
          <div class="row-text"><b>${two(event[0])}:${two(event[1])}</b><span><i class="chipm m${event[2]}"></i>${esc(t.scheduleModes[event[2]])}</span></div>
          <div class="row-value">${event[3] ? `${event[3]}°` : ""}</div>${icon("chevron", "go")}</button>`
      )
      .join("");
    const dirty = JSON.stringify(top.events) !== JSON.stringify(this._activeEvents(top.day));
    return `${this._bar(t.days[top.day], this._title("schedule"), false)}
      <div class="body">
        ${rows ? `<div class="group">${rows}</div>` : `<div class="empty">${esc(t.noEvents)}</div>`}
        ${top.events.length < EVENTS ? `<button class="wide soft" data-do="add-event">${icon("plus")}${esc(t.addEvent)}</button>` : ""}
        ${dirty ? `<button class="wide" data-do="save-day">${icon("check")}${esc(t.save)}</button>` : `<button class="wide soft" data-do="copy-day">${icon("copy")}${esc(t.copyDay)}</button>`}
      </div>`;
  }

  _view_event(top) {
    const t = this._t;
    const event = top.event;
    const stepper = (field, label, value) => `<div class="field"><span>${esc(label)}</span><button data-hold-event="${field}:-1" aria-label="−">${icon("minus")}</button>
      <b id="ev-${field}">${value}</b><button data-hold-event="${field}:1" aria-label="+">${icon("plus")}</button></div>`;
    const chips = [1, 2, 3, 4, 5]
      .map((mode) => `<button data-ev-mode="${mode}" class="${event[2] === mode ? "on" : ""}">${esc(t.scheduleModes[mode])}</button>`)
      .join("");
    return `${this._bar(t.event, t.days[top.day], false)}
      <div class="body">
        ${stepper("hour", t.hours, two(event[0]))}
        ${stepper("minute", t.minutes, two(event[1]))}
        <div class="chips">${chips}</div>
        ${stepper("temp", "°C", event[3])}
        <div class="foot">
          ${top.index === null ? "" : `<button data-do="remove-event">${esc(t.remove)}</button>`}
          <button class="main" data-do="event-ok">${esc(t.ok)}</button>
        </div>
      </div>`;
  }

  _stepEvent(field, direction) {
    const event = this._top.event;
    if (field === "hour") event[0] = (event[0] + direction + 24) % 24;
    if (field === "minute") event[1] = (event[1] + direction * 5 + 60) % 60;
    if (field === "temp") event[3] = Math.min(30, Math.max(0, event[3] + direction));
    const text = { hour: two(event[0]), minute: two(event[1]), temp: String(event[3]) }[field];
    this.shadowRoot.getElementById(`ev-${field}`).textContent = text;
  }

  _finishEvent(remove) {
    const top = this._top;
    const day = this._stack[this._stack.length - 2];
    if (remove) day.events.splice(top.index, 1);
    else if (top.index === null) day.events.push(top.event);
    else day.events[top.index] = top.event;
    this._back();
  }

  async _saveDay() {
    const top = this._top;
    const events = top.events.slice().sort((a, b) => minutes(a) - minutes(b));
    while (events.length < EVENTS) events.push([0, 0, 0, 0]);
    try {
      const result = await this._call("schedule_write", { day: top.day, events });
      this._days = result.days;
      top.events = this._activeEvents(top.day);
      this._toast(this._t.saved);
      this._draw();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _view_copy(top) {
    const t = this._t;
    const chips = t.days
      .map((name, day) => (day === top.day ? "" : `<button data-copy="${day}" class="${top.targets.includes(day) ? "on" : ""}">${esc(name)}</button>`))
      .join("");
    return `${this._bar(t.copyTo, t.days[top.day], false)}
      <div class="body"><div class="chips">${chips}</div>
        <button class="wide" data-do="copy-run" ${top.targets.length ? "" : "disabled"}>${icon("copy")}${esc(t.copy)}</button></div>`;
  }

  async _copyDay() {
    const top = this._top;
    try {
      const result = await this._call("schedule_copy", { source: top.day, targets: top.targets });
      this._days = result.days;
      this._toast(this._t.saved);
      this._back();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  // readings

  _view_readings() {
    const t = this._t;
    const present = {};
    this._schema.datapoints.forEach((item) => {
      present[item.section] = true;
    });
    const rows = Object.keys(READINGS)
      .filter((section) => present[section])
      .map((section) => `<button class="row" data-reading="${section}"><div class="box">${icon(READINGS[section])}</div><div class="row-text"><b>${esc(this._readingTitle(section))}</b></div>${icon("chevron", "go")}</button>`)
      .join("");
    return `${this._bar(this._title("readings"), t.menu)}
      <div class="body"><button class="wide soft" data-do="flow">${icon("flow")}${esc(t.flow)}</button><div class="group">${rows}</div></div>`;
  }

  _view_values(top) {
    const rows = this._schema.datapoints
      .filter((item) => item.section === top.section)
      .map((item) => `<div class="row"><div class="row-text"><b>${esc(item.label)}</b></div><div class="row-value" data-dp="${esc(item.name)}"></div></div>`)
      .join("");
    return `${this._bar(this._readingTitle(top.section), this._title("readings"))}<div class="body"><div class="group">${rows}</div></div>`;
  }

  _readingTitle(section) {
    const titles = TITLES[`r_${section}`] || [section, section, section];
    return titles[{ ru: 0, lv: 1, en: 2 }[this._lang]];
  }

  _view_flow() {
    const t = this._t;
    const efficiency = this._status.virtual.recovery_efficiency;
    const fan = (label, output, rpm, flow) => `<div><span>${esc(label)}</span><b data-dp="${output}"></b>
      <small>${esc(this._reading(rpm))}${this._dp[flow] ? ` · ${esc(this._reading(flow))}` : ""}</small></div>`;
    return `${this._bar(t.flow, t.recovery)}
      <div class="body">
        <div class="scheme">
          <svg viewBox="50 34 420 232" aria-hidden="true">
            <rect class="body-unit" x="120" y="44" width="280" height="212" rx="16"/>
            <path class="line-fresh" d="M120 62 H165 L355 238 H400"/>
            <path class="line-stale" d="M400 62 H355 L165 238 H120"/>
            <polygon class="core" points="260,92 318,150 260,208 202,150"/>
            <text class="core-text" x="260" y="159">${efficiency === undefined ? "—" : `${this._number(efficiency)}%`}</text>
          </svg>
          <div class="port tl"><span>${esc(t.outdoor)}</span><b data-deg="T_Outdoor"></b></div>
          <div class="port tr"><span>${esc(t.fromRooms)}</span><b data-deg="T_Extract"></b></div>
          <div class="port bl"><b data-deg="T_Exhaust"></b><span>${esc(t.exhaust)}</span></div>
          <div class="port br"><b data-deg="T_Supply"></b><span>${esc(t.toRooms)}</span></div>
        </div>
        <div class="pair">${fan(t.supply, "Fan1_Output", "Fan1_RPM", "Airflow_Supply")}${fan(t.extract, "Fan2_Output", "Fan2_RPM", "Airflow_Exhaust")}</div>
      </div>`;
  }

  // faults

  _faultName(fault) {
    if (fault.name && this._faultNames[fault.name]) return this._faultNames[fault.name];
    if (fault.word !== undefined) return this._t.bit(fault.word, fault.bit);
    const raw = (fault.id || "").split(":").pop();
    return raw.includes(".") ? this._t.bit(raw.split(".")[0], raw.split(".")[1]) : raw;
  }

  _view_faults() {
    const t = this._t;
    const faults = this._status.faults;
    const rows = faults
      .map((fault) => `<div class="row"><span class="kind ${esc(fault.kind)}">${esc(t.kinds[fault.kind])}</span><div class="row-text"><b>${esc(this._faultName(fault))}</b></div></div>`)
      .join("");
    return `${this._bar(this._title("faults"), t.active)}
      <div class="body">
        ${rows ? `<div class="group">${rows}</div>` : `<div class="empty">${esc(t.noFaults)}</div>`}
        <button class="wide" data-press="ResetErrors">${esc(t.resetErrors)}</button>
        <div class="group">
          <button class="row" data-do="history"><div class="box">${icon("clock")}</div><div class="row-text"><b>${esc(t.history)}</b></div>${icon("chevron", "go")}</button>
          <button class="row" data-do="words"><div class="box">${icon("chip")}</div><div class="row-text"><b>${esc(t.words)}</b></div>${icon("chevron", "go")}</button>
        </div>
      </div>`;
  }

  _view_history(top) {
    const t = this._t;
    const log = top.log;
    let body = `<div class="empty">${esc(t.loading)}</div>`;
    if (log) {
      const when = new Intl.DateTimeFormat(t.locale, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
      const rows = log
        .map((item) => `<div class="row"><span class="kind ${item.on ? esc(item.kind) : "gone"}">${esc(item.on ? t.appeared : t.cleared)}</span>
          <div class="row-text"><b>${esc(this._faultName(item))}</b><span>${esc(when.format(new Date(item.at)))}</span></div></div>`)
        .join("");
      body = rows ? `<div class="group">${rows}</div>` : `<div class="empty">${esc(t.noHistory)}</div>`;
      if (rows && this._admin) body += `<button class="wide danger" data-do="clear-log">${esc(t.clearHistory)}</button>`;
    }
    return `${this._bar(t.history, this._title("faults"))}<div class="body">${body}</div>`;
  }

  async _loadHistory() {
    const top = this._top;
    if (top.log) return;
    try {
      const result = await this._call("log");
      top.log = result.log;
      if (this._top === top) this._draw();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _view_words() {
    const rows = Object.keys(this._status.words)
      .map((name) => {
        const value = this._status.words[name];
        return `<div>${esc(name)}: ${value === null || value === undefined ? "—" : `0x${value.toString(16).toUpperCase().padStart(4, "0")}`}</div>`;
      })
      .join("");
    return `${this._bar(this._t.words, this._title("faults"))}<div class="body"><div class="group words">${rows}</div></div>`;
  }

  // service access

  _view_pin(top) {
    const t = this._t;
    if (!this._admin) return `${this._bar(this._title("service"), t.menu)}<div class="center">${esc(t.needAdmin)}</div>`;
    const dots = [0, 1, 2, 3].map((at) => `<i class="${at < (top.entered || "").length ? "on" : ""}"></i>`).join("");
    const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "ok"]
      .map((key) => {
        if (key === "ok") return `<button class="main" data-pin="ok">${esc(t.ok)}</button>`;
        return `<button data-pin="${key}">${key === "⌫" ? icon("erase") : key}</button>`;
      })
      .join("");
    return `${this._bar(t.pin, t.pinHint)}
      <div class="body"><div class="editor"><div class="dots" id="pin-dots">${dots}</div><div class="grow"></div><div class="keys">${keys}</div></div></div>`;
  }

  async _pinKey(key) {
    const top = this._top;
    top.entered = top.entered || "";
    if (key === "⌫") top.entered = top.entered.slice(0, -1);
    else if (key !== "ok" && top.entered.length < 4) top.entered += key;
    this.shadowRoot.querySelectorAll("#pin-dots i").forEach((dot, at) => dot.classList.toggle("on", at < top.entered.length));
    if (key !== "ok" || !top.entered) return;
    const pin = top.entered;
    top.entered = "";
    this.shadowRoot.querySelectorAll("#pin-dots i").forEach((dot) => dot.classList.remove("on"));
    try {
      const result = await this._call("unlock", { pin });
      this._token = result.token;
      this._tokenUntil = Date.now() / 1000 + result.seconds;
      const then = top.then;
      this._stack.pop();
      this._open(then);
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _lock() {
    this._token = null;
    if (this._stack.some((entry) => entry.id && this._nodes[entry.id] && this._nodes[entry.id].service)) this._goHome();
  }

  _left() {
    const left = Math.max(0, Math.round(this._tokenUntil - Date.now() / 1000));
    return `${Math.floor(left / 60)}:${two(left % 60)}`;
  }

  // system screens

  _view_screen() {
    const t = this._t;
    const theme = this._state(THEME_ENTITY) || stored.get("theme") || "auto";
    const language = this._lang;
    const accent = this._state(ACCENT_ENTITY) || stored.get("accent") || "blue";
    const layout = `<div class="caption">${esc(t.homeLayout)}</div>
        <div class="seg">${LAYOUTS.map((name) => `<button data-look="layout:${name}" class="${name === this._layout ? "on" : ""}">${esc(t.layouts[name])}</button>`).join("")}</div>`;
    // hosted in a card, the card keeps the look; the home screen is still chosen here
    if (this._embed) return `${this._bar(this._title("screen"), this._title("system"))}<div class="body">${layout}</div>`;
    return `${this._bar(this._title("screen"), this._title("system"))}
      <div class="body">
        ${layout}
        <div class="caption">${esc(t.theme)}</div>
        <div class="seg">${THEMES.map((name) => `<button data-look="theme:${name}" class="${name === theme ? "on" : ""}">${esc(t.themes[name])}</button>`).join("")}</div>
        <div class="caption">${esc(t.accent)}</div>
        <div class="swatches">${Object.keys(ACCENTS).map((name) => `<button data-look="accent:${name}" style="background:${ACCENTS[name]}" aria-label="${name}">${name === accent ? icon("check") : ""}</button>`).join("")}</div>
        <div class="caption">${esc(t.language)}</div>
        <div class="seg">${Object.keys(LANGUAGES).map((name) => `<button data-look="language:${name}" class="${name === language ? "on" : ""}">${LANGUAGES[name]}</button>`).join("")}</div>
        <div class="caption">${esc(t.menuButton)}</div>
        <div class="group"><button class="row" data-do="targets"><div class="box">${icon("exit")}</div>
          <div class="row-text"><b>${esc(this._homeName())}</b></div>${icon("chevron", "go")}</button></div>
      </div>`;
  }

  // where the menu's button leads: every panel, and each view of a dashboard

  _view_targets(top) {
    const t = this._t;
    const current = this._homeTarget();
    const rows = (top.list || [])
      .map((entry) => `<button class="row" data-target="${esc(entry.path)}"><div class="row-text"><b>${esc(entry.title)}</b>${entry.view ? `<span>${esc(entry.view)}</span>` : ""}</div>${entry.path === current ? icon("check") : ""}</button>`)
      .join("");
    return `${this._bar(t.menuButton, t.leadsTo, false)}
      <div class="body">${rows ? `<div class="group">${rows}</div>` : `<div class="empty">${esc(t.loading)}</div>`}</div>`;
  }

  async _panelTargets(panel) {
    const path = `/${panel.url_path}`;
    const title = this._panelTitle(panel);
    if (panel.component_name !== "lovelace") return [{ path, title }];
    try {
      const config = await this._hass.callWS({ type: "lovelace/config", url_path: panel.url_path });
      const views = (config.views || []).filter((view) => !view.subview);
      if (views.length) return views.map((view, index) => ({ path: `${path}/${view.path || index}`, title, view: view.title || view.path || String(index + 1) }));
    } catch (err) {
      // a dashboard made by a strategy has no views to list; it can still be opened as a whole
    }
    return [{ path, title }];
  }

  async _loadTargets() {
    const top = this._top;
    if (top.list) return;
    const panels = Object.keys(this._hass.panels)
      .map((key) => this._hass.panels[key])
      .filter((panel) => panel.title && !panel.url_path.startsWith("_") && !NOT_TARGETS.includes(panel.url_path))
      .sort((a, b) => (b.component_name === "lovelace") - (a.component_name === "lovelace"));
    const found = await Promise.all(panels.map((panel) => this._panelTargets(panel)));
    top.list = [{ path: "/", title: "Home Assistant" }].concat(...found);
    if (this._top === top) this._draw();
  }

  async _setHome(path) {
    stored.set("home", path);
    const shared = this._state(HOME_ENTITY) !== null;
    try {
      if (shared) await this._hass.callService("input_text", "set_value", { entity_id: HOME_ENTITY, value: path });
      this._toast(this._t.saved);
    } catch (err) {
      this._toast(this._problem(err));
    }
    setTimeout(() => this._back(), shared ? 400 : 0);
  }

  async _setLook(key, value) {
    const entity = { theme: THEME_ENTITY, accent: ACCENT_ENTITY, language: LANGUAGE_ENTITY }[key];
    stored.set(key, value);
    if (this._state(entity) !== null) {
      await this._hass.callService("input_select", "select_option", { entity_id: entity, option: value });
    }
    setTimeout(() => {
      this._look();
      this._draw();
    }, this._state(entity) !== null ? 400 : 0);
  }

  _view_about() {
    const t = this._t;
    const unit = (this._units || []).find((candidate) => candidate.entry_id === this._entry) || {};
    const fact = (name, value) => `<div class="row"><div class="row-text"><b>${esc(name)}</b></div><div class="row-value">${esc(or(value, "—"))}</div></div>`;
    const others =
      (this._units || []).length > 1
        ? `<div class="group">${this._units
            .map((candidate) => `<button class="row" data-unit="${esc(candidate.entry_id)}"><div class="row-text"><b>${esc(candidate.title)}</b></div>${candidate.entry_id === this._entry ? icon("check") : ""}</button>`)
            .join("")}</div>`
        : "";
    return `${this._bar(this._title("about"), this._title("system"))}
      <div class="body">${others}<div class="group">
        ${fact(t.runningHours, this._status.virtual.running_hours)}
        ${fact(t.firmware, unit.firmware)}${fact(t.bootloader, unit.bootloader)}
        ${fact(t.host, unit.host)}${fact(t.port, unit.port)}${fact(t.unitId, unit.unit)}
        ${fact(t.protocol, unit.framing === "rtu" ? "RTU over TCP" : "Modbus TCP")}
        ${fact(t.ip, this._status.virtual.ip)}${fact(t.mac, this._status.virtual.mac)}
        ${fact(t.eeprom, this._dp.WriteToEepromCounter)}
      </div></div>`;
  }

  async _switchUnit(entry) {
    this._leave();
    this._entry = entry;
    this._ready = false;
    this._token = null;
    this._days = null;
    this._dp = {};
    this._sp = {};
    this._stack = [{ view: "home" }];
    this._message(this._t.loading);
    try {
      await this._load();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  // overlays

  _ask(text, detail = "") {
    const t = this._t;
    return new Promise((resolve) => {
      const shade = document.createElement("div");
      shade.className = "shade";
      shade.innerHTML = `<div class="ask"><p>${esc(text)}</p>${detail ? `<p class="small">${esc(detail)}</p>` : ""}
        <div class="foot"><button data-answer="no">${esc(t.cancel)}</button><button class="main" data-answer="yes">${esc(t.confirm)}</button></div></div>`;
      shade.addEventListener("click", (event) => {
        const button = event.target.closest("[data-answer]");
        if (!button) return;
        event.stopPropagation();
        shade.remove();
        resolve(button.dataset.answer === "yes");
      });
      this.shadowRoot.querySelector(".app").appendChild(shade);
    });
  }

  _toast(text) {
    const app = this.shadowRoot.querySelector(".app");
    const shown = app.querySelector(".toast");
    if (shown) shown.remove();
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = text;
    app.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
  }

  // input

  _tick() {
    if (this._top.view === "home" && this._ready) {
      const time = this.shadowRoot.getElementById("h-time");
      if (time && time.textContent !== this._clock()) time.textContent = this._clock();
    }
    if (this._token && Date.now() / 1000 >= this._tokenUntil) this._lock();
    const left = this.shadowRoot.getElementById("service-left");
    if (left && this._token) left.textContent = this._t.open(this._left());
    const quiet = Date.now() - this._last > IDLE_MS;
    if (quiet && this._top.sheet && this._ready) this._closeSheet();
    const busy = ["editor", "event", "day", "copy", "pin"].includes(this._top.view);
    if (quiet && this._stack.length > 1 && !busy && this._ready) {
      this._token = null;
      this._goHome();
    }
  }

  _onClick(event) {
    const node = event.target.closest(
      "[data-do],[data-node],[data-edit],[data-press],[data-mode],[data-pick],[data-day],[data-event],[data-copy],[data-ev-mode],[data-reading],[data-key],[data-pin],[data-look],[data-unit],[data-target]"
    );
    if (!node || node.disabled) return;
    const data = node.dataset;
    if (data.do) this._action(data.do, node);
    else if (data.node) this._open(data.node);
    else if (data.edit) this._edit(data.edit);
    else if (data.press) this._press(data.press);
    else if (data.mode !== undefined) {
      this._control({ action: "set_mode", mode: Number(data.mode) });
      this._closeSheet();
    }
    else if (data.pick !== undefined) this._pick(Number(data.pick));
    else if (data.day !== undefined) this._openDay(Number(data.day));
    else if (data.event !== undefined) this._openEvent(Number(data.event));
    else if (data.copy !== undefined) this._toggleCopy(Number(data.copy));
    else if (data.evMode !== undefined) this._eventMode(Number(data.evMode));
    else if (data.reading) this._go("values", { section: data.reading });
    else if (data.key !== undefined) this._key(data.key);
    else if (data.pin !== undefined) this._pinKey(data.pin);
    else if (data.look) this._setLook(data.look.split(":")[0], data.look.split(":")[1]);
    else if (data.unit) this._switchUnit(data.unit);
    else if (data.target) this._setHome(data.target);
  }

  _action(name, node) {
    const top = this._top;
    switch (name) {
      case "back": this._leaveScreen(); break;
      case "home": this._goHome(); break;
      case "menu": this._go("menu"); break;
      case "exit": this._exit(); break;
      case "targets": this._go("targets"); break;
      case "temp": this._go("temp"); break;
      case "flow": this._go("flow"); break;
      case "air": this._open(this._airValue()[0] === this._t.recovery ? "readings" : "air"); break;
      case "target": break;
      case "auto":
        this._control({ action: "set_auto" });
        this._closeSheet();
        break;
      case "sheet": this._openSheet(node.dataset.sheet); break;
      case "sheet-close": this._closeSheet(); break;
      case "sync": this._control({ action: "sync_clock" }, true); break;
      case "save": this._saveEditor(); break;
      case "keys-on":
        top.typing = true;
        top.text = "";
        this._draw();
        break;
      case "keys-off":
        top.typing = false;
        this._draw();
        break;
      case "keys-ok": this._typed(); break;
      case "add-event": this._go("event", { day: top.day, index: null, event: top.events.length ? top.events[top.events.length - 1].slice() : [8, 0, 4, 20] }); break;
      case "save-day": this._saveDay(); break;
      case "copy-day": this._go("copy", { day: top.day, targets: [] }); break;
      case "copy-run": this._copyDay(); break;
      case "event-ok": this._finishEvent(false); break;
      case "remove-event": this._finishEvent(true); break;
      case "history": this._go("history"); break;
      case "words": this._go("words"); break;
      case "clear-log": this._clearLog(); break;
      case "lock": this._lock(); break;
      default: break;
    }
  }

  async _leaveScreen() {
    const top = this._top;
    if (top.view === "day" && JSON.stringify(top.events) !== JSON.stringify(this._activeEvents(top.day))) {
      if (!(await this._ask(this._t.leave, this._t.unsaved))) return;
    }
    this._back();
  }

  _edit(name) {
    const item = this._setpoints[name];
    if (item.kind === "select") this._go("options", { name });
    else this._go("editor", { name });
  }

  async _pick(value) {
    const item = this._setpoints[this._top.name];
    if (item.name === "OperatingMode") {
      await this._control({ action: "set_mode", mode: value });
      this._back();
    } else if (await this._write(item, value)) this._back();
  }

  async _press(name) {
    const t = this._t;
    const item = this._setpoints[name];
    if (name === "Filter_Reset" && !(await this._ask(t.filterAsk))) return;
    if (item.danger && !(await this._ask(item.label, t.dangerRun))) return;
    const fields = { name };
    if (item.level === "service") fields.token = this._token;
    if (item.danger) fields.confirm = true;
    try {
      await this._call("write", fields);
      this._toast(t.saved);
    } catch (err) {
      this._failed(err);
    }
  }

  async _control(fields, confirmSaved) {
    try {
      await this._call("control", fields);
      if (confirmSaved) this._toast(this._t.saved);
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _openEvent(index) {
    const top = this._top;
    this._go("event", { day: top.day, index, event: top.events[index].slice() });
  }

  _eventMode(mode) {
    this._top.event[2] = mode;
    this._draw();
  }

  _toggleCopy(day) {
    const top = this._top;
    const at = top.targets.indexOf(day);
    if (at >= 0) top.targets.splice(at, 1);
    else top.targets.push(day);
    this._draw();
  }

  _key(key) {
    const top = this._top;
    const text = top.text || "";
    if (key === "⌫") top.text = text.slice(0, -1);
    else if (key === "-") top.text = text.startsWith("-") ? text.slice(1) : `-${text}`;
    else if (key === ",") top.text = text.includes(",") ? text : `${text || "0"},`;
    else top.text = text.length < 8 ? text + key : text;
    this.shadowRoot.getElementById("ed-value").textContent = top.text || "0";
  }

  _typed() {
    const top = this._top;
    const item = this._setpoints[top.name];
    const value = Number((top.text || "0").replace(",", "."));
    top.value = Math.min(item.max, Math.max(item.min, Number.isNaN(value) ? top.value : Number(value.toFixed(item.decimals))));
    top.typing = false;
    this._draw();
  }

  async _clearLog() {
    if (!(await this._ask(this._t.clearAsk))) return;
    try {
      await this._call("log_clear");
      this._top.log = [];
      this._draw();
    } catch (err) {
      this._toast(this._problem(err));
    }
  }

  _onChange(event) {
    const node = event.target;
    if (node.matches("[data-switch]")) this._toggle(node);
  }

  async _toggle(node) {
    const item = this._setpoints[node.dataset.switch];
    const value = node.checked ? 1 : 0;
    node.dataset.busy = "1";
    const done = await this._write(item, value);
    delete node.dataset.busy;
    if (!done) node.checked = Boolean(this._sp[item.name]);
  }

  _onInput(event) {
    if (event.target.id !== "ed-slider") return;
    this._top.value = Number(event.target.value);
    this._showValue();
  }

  // the steppers repeat while held, faster the longer they are held

  _onPress(event) {
    const hold = event.target.closest("[data-hold],[data-hold-event],[data-fan]");
    const target = event.target.closest('[data-do="target"]');
    if (target) {
      this._nudgeTarget(Number(target.dataset.step));
      return;
    }
    if (!hold || hold.disabled) return;
    let step;
    if (hold.dataset.fan) step = () => this._nudgeFan(Number(hold.dataset.fan));
    else if (hold.dataset.hold) step = (factor) => this._stepValue(Number(hold.dataset.hold), factor);
    else {
      step = () => {
        const parts = hold.dataset.holdEvent.split(":");
        this._stepEvent(parts[0], Number(parts[1]));
      };
    }
    step(1);
    let count = 0;
    this._stopHold();
    this._holdWait = setTimeout(() => {
      this._holdTimer = setInterval(() => {
        count += 1;
        step(count > 20 ? 10 : 1);
      }, 110);
    }, 420);
  }

  _stopHold() {
    clearTimeout(this._holdWait);
    clearInterval(this._holdTimer);
  }

  _swipeStart(event) {
    const touch = event.touches[0];
    this._swipe = event.target.closest && event.target.closest("input") ? null : { x: touch.clientX, y: touch.clientY };
  }

  _swipeEnd(event) {
    const from = this._swipe;
    this._swipe = null;
    if (!from || this._stack.length < 2) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - from.x;
    const dy = Math.abs(touch.clientY - from.y);
    if (dx > 90 && dy < 50) this._leaveScreen();
  }
}

AlpicAirNestWall.TREE = TREE;
AlpicAirNestWall.TITLES = TITLES;
AlpicAirNestWall.STRINGS = STRINGS;
AlpicAirNestWall.EMBED = 1;

if (!customElements.get("alpicair-nest-wall")) customElements.define("alpicair-nest-wall", AlpicAirNestWall);
