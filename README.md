# AlpicAir NEST for Home Assistant

[Русский](#русский) · [English](#english)

## Русский

Интеграция для рекуператоров **AlpicAir NEST** (контроллер MCB) и **AlpicAir NEST LS** (контроллер ES1125). Модель выбирается при добавлении. Подключается по Modbus TCP напрямую, без облака. Панель настроек, данных, расписания, сервиса и ошибок встроена в интеграцию и появляется в боковом меню Home Assistant.

> **Статус NEST LS: чтение проверено на настоящей установке** (прошивка 49012, таблица регистров 48012): поиск в сети, все показания и настройки. Управление режимами на настоящей установке ещё не проверялось, см. раздел [«Что проверить на установке»](#что-проверить-на-установке). Сервисные настройки меняйте осторожно.

> **Статус NEST: на настоящей установке не проверялось.** Поддержка сделана по таблице Modbus MCB 1.27 и проверена только на симуляторе, см. там же.

### Установка

Через HACS: **HACS → Integrations → ⋮ → Custom repositories**, адрес этого репозитория, категория **Integration**. Затем установите **AlpicAir NEST** и перезапустите Home Assistant.

Вручную: скопируйте папку `custom_components/alpicair_nest` в `config/custom_components/` и перезапустите Home Assistant.

На установке должен быть включён Modbus TCP, порт по умолчанию 502.

### Подключение

**Настройки → Устройства и службы → Добавить интеграцию → AlpicAir NEST**. Сначала выберите модель: **NEST** или **NEST LS**. У них разные контроллеры и разные таблицы регистров, поэтому установка другой модели не опознаётся. Установки, добавленные до появления выбора, считаются NEST LS. Затем на выбор:

- **Ввести IP-адрес**: адрес, порт и, если нужно, адрес Modbus. Пустое поле означает автоматический подбор.
- **Найти автоматически**: поиск по локальным сетям Home Assistant. Установка опознаётся по своим регистрам, поиск только читает.

Если адрес установки сменился, откройте её настройки и выберите **Перенастроить**. Интервал опроса и показ панели меняются в **Настроить**.

### Панель

| Вкладка | Что на ней |
| --- | --- |
| Обзор | Схема потоков с температурами и эффективностью, режимы, уставка, расход, фильтр |
| Настройки | Температуры, качество воздуха, свободное охлаждение, вентиляторы, время, система |
| Расписание | Неделя, 7 дней по 10 событий, копирование дня на другие дни |
| Данные | Все показания установки по разделам, с поиском |
| Сервис | Настройки оборудования, входов, клапанов, сети; перезапуск, калибровка, точки восстановления |
| Ошибки | Активные ошибки и предупреждения, сброс, история, слова состояния |

### Панель для NSPanel Pro

Для квадратного SONOFF NSPanel Pro (480×480) есть отдельная панель: пункт **NEST NSPanel** в боковом меню, адрес `/alpicair-nest-wall`. Она рисуется под палец и не требует экранной клавиатуры: числа меняются кнопками − и +, ползунком или встроенной цифровой клавиатурой.

- **Главный экран «Дом»** (по умолчанию): контур дома с рекуператором в центре: потоки с улицы в комнаты и из комнат наружу перекрещиваются в нём, у концов потоков — их температуры, в центре рекуператора — скорость вентиляторов, внизу — режим. Нажатие на режим, температуру или скорость открывает полупрозрачное окно поверх экрана: режим закрывается сразу после выбора, температура и скорость — касанием вне окна. Значок в правом верхнем углу появляется при ошибках и открывает их.
- **Главный экран «Вентилятор»:** режим, скорость вентиляторов с кнопками − и + (крупно, в центре, под ней текущий режим; нажатие на круг открывает режимы), четыре температуры, цель по температуре, влажность. Кнопки меняют скорость текущего режима сразу у обоих вентиляторов, разница между ними сохраняется. Менять скорость могут администраторы.
- **Меню:** Режим, Климат, Вентиляция, Качество воздуха, Расписание, Показания, Ошибки, Система, Сервис и кнопка перехода на другую панель.
- **Подменю:** через них доступна каждая из 368 настроек установки. Сервис открывается PIN-клавиатурой.
- **Расписание:** неделя, правка событий, копирование дня.
- Через две минуты без касаний панель возвращается на главный экран и закрывает сервис. Назад можно вернуться кнопкой или свайпом вправо.

Вид главного экрана, язык, тема и цвет меняются в **Система → Экран панели**. Если в Home Assistant есть `input_select.nspanel_language`, `input_select.nspanel_theme` и `input_select.nspanel_accent`, панель берёт значения из них. Иначе выбор хранится на устройстве.

Куда ведёт кнопка в меню, выбирается значком рядом с ней или там же, в **Система → Экран панели**: из списка панелей и видов дашбордов. Выбор хранится на устройстве, а если есть `input_text.nspanel_home`, то в нём, и тогда он общий для всех устройств.

Параметры адреса: `?lang=lv`, `?theme=dark`, `?accent=teal`, `?home=/путь` (куда вести кнопка выхода), `?unit=<entry_id>`. Показ в боковом меню отключается в **Настроить**.

Файл панели рассчитан на старый WebView Android 8.1, это проверяет `tests/check_panels.js`. Есть и второй вариант: основная панель на квадратном экране сама переходит на компактную раскладку (`/alpicair-nest`, `?compact=1` или `?compact=0`).

Кто что может менять:

| Уровень | Кто | Что |
| --- | --- | --- |
| Пользователь | любой вошедший | режимы, уставки, расписание |
| Наладчик | администратор | скорости вентиляторов, вытяжка, временные режимы |
| Сервис | администратор с сервисным PIN | всё остальное |

PIN сверяется с тем, что записан в самой установке, и нигде не хранится. Доступ открывается на 15 минут; после 5 неверных попыток ввод блокируется на минуту. Проверка выполняется на сервере, а не только в панели. Опасные действия дополнительно подтверждаются.

### Объекты

- `climate.alpicair_nest`: включение, режимы как пресеты, целевая температура.
- Датчики температур, расхода, оборотов, давления, фильтра, эффективности рекуперации, числа ошибок. Датчики влажности, CO₂ и VOC включаются, только если соответствующий аналоговый вход настроен.
- Переключатели и числа для повседневных настроек. Большинство отключено по умолчанию, включить можно на странице устройства.
- Кнопки: сброс фильтра, сброс ошибок, установка часов по Home Assistant.
- Сервисные настройки объектами не становятся, они есть только в панели.
- Событие `alpicair_nest_fault` при каждой новой неисправности, для автоматизаций.

Значения пишутся только при изменении: многие настройки лежат в EEPROM, у которого ограничен ресурс записи. Поэтому не стоит менять их автоматизациями часто.

### Что проверить на установке

Проверено на настоящей установке (прошивка 49012):

- Setpoints читаются функцией 3, Datapoints функцией 4, адресация с нуля. Все 348 настроек лежат в своих диапазонах, недоступных адресов нет.
- Порядок битов в словах ошибок: сработавший бит совпал с отдельным флагом той же ошибки.

Ещё не проверено:

1. **Вентиляторы.** Принято, что вентилятор 1 приточный, вентилятор 2 вытяжной.
2. **Управление режимом.** Чтобы режим не перезаписывался расписанием, сначала ставится `ControlMode = Manual`, затем `OperatingMode`. Кнопка «По расписанию» возвращает `Auto`.
3. **Уровни доступа.** В таблице у всех регистров указан уровень User, разделение на три уровня сделано здесь.

Установка повторяет ошибки и предупреждения в словах Alarm, поэтому одна неисправность показывается одной строкой. Без датчиков давления расход равен нулю, и панель показывает выход вентиляторов в процентах.

#### NEST (контроллер MCB)

На настоящей установке не проверено ничего. В первую очередь:

1. **Адресация.** Адреса берутся из таблицы как есть: регистр 1 запрашивается по адресу 1. Используются функции 1, 2, 3, 4, 5, 6 и 16.
2. **Режим 4 в текущем режиме.** Принято, что `Current system mode = 4` означает буст. Буст включается и выключается катушкой 5, остальные режимы регистром 1.
3. **Сервисный PIN.** PIN записывается в регистр 199, после чего читается открытый уровень доступа (входной регистр 106). Нужно проверить, что установка открывает уровень именно так и требует ли она пароль наладчика для настроек этого уровня.
4. **Сохранение настроек.** Неизвестно, сохраняются ли изменения сами или нужна команда «Сохранить настройки в память установки» (катушка 51). Она есть среди кнопок.
5. **Часы.** Дата и время пишутся в регистры 100–102 и 104–106, затем подаётся команда катушкой 2.
6. **Давление в каналах.** Множитель зависит от настройки «Множитель давления воздуха»; принято 0,1.
7. **Датчики влажности и CO₂.** Плитки появляются, если датчик задан в настройках или от него приходит ненулевое значение.

Недельное расписание и отпуск у NEST устроены иначе, чем у NEST LS (10 событий с днями недели), поэтому вкладки «Расписание» у него нет: события настраиваются в **Настройки → Недельное расписание** и **Отпуск**. Дни недели задаются суммой: понедельник 1, вторник 2, среда 4, четверг 8, пятница 16, суббота 32, воскресенье 64. Режима «По расписанию» и режима кухонной вытяжки у NEST нет. Сетевого адреса у контроллера MCB нет, поэтому установка опознаётся по своему номеру (ID), а если он не задан, по адресу подключения.

Если что-то не сходится, приложите диагностику: страница устройства → **Скачать диагностику**. Адреса и PIN в неё не попадают.

### Разработка

```bash
pip install -r requirements_test.txt
pytest

# симулятор установки на порту 5020
python -m tests.simulator --port 5020 --faults
# то же для NEST
python -m tests.simulator --port 5021 --model nest --faults
```

`custom_components/alpicair_nest/registers_nest.json` (NEST) создаётся командой `scripts/build_registers_nest.py <таблица.xlsx>`, названия на трёх языках лежат в `scripts/labels_nest.py`. Пароли, заводские функции, принудительное управление выходами, карта входов и выходов и регистры для записи показаний из BMS в карту не попадают.

`custom_components/alpicair_nest/registers.json` (NEST LS) создаётся из таблицы производителя командой `scripts/build_registers.py <файл.xlsm>`. Сама таблица в репозитории не хранится. Ключи Bluetooth и Nabto, PIN-коды, заводские записи и принудительное управление выходами скрипт отбрасывает.

## English

Local Modbus TCP integration for **AlpicAir NEST** (MCB controller) and **AlpicAir NEST LS** (ES1125 controller) heat-recovery units; the model is chosen when the unit is added. It comes with a built-in sidebar panel for settings, schedule, data, service and faults. No cloud.

> **NEST status: not tried on a real unit.** It is built from the MCB 1.27 Modbus table and tested against a simulator only.
>
> **NEST LS status: reading is verified on a real unit** (firmware 49012, register table 48012): network search, all readings and settings. Mode control has not been tried on a real unit yet, see [What to check on a real unit](#what-to-check-on-a-real-unit).

### Install

With HACS: add this repository under **HACS → Integrations → ⋮ → Custom repositories** with category **Integration**, install **AlpicAir NEST** and restart Home Assistant. Or copy `custom_components/alpicair_nest` into `config/custom_components/`.

Modbus TCP must be enabled on the unit (port 502 by default).

### Set up

**Settings → Devices & services → Add integration → AlpicAir NEST**, choose **NEST** or **NEST LS** (units added before the choice existed are NEST LS), then either enter the IP address or let it search the local networks. The search only reads, and recognises a unit by its registers.

### Square wall panels

The SONOFF NSPanel Pro (480×480) has a panel of its own: **NEST NSPanel** in the sidebar, at `/alpicair-nest-wall`. It has a home screen, a menu and submenus that reach all 368 settings, a schedule editor, faults and service access with an on-screen PIN pad, and it needs no on-screen keyboard. It returns to the home screen after two minutes without a touch.

The home screen shows the house by default: the outline of the house with the recuperator in the middle, the two air flows crossing in it, the four temperatures at the ends of the flows, fan speed in the centre of the recuperator, the mode below it, and a fault badge in the top right corner that opens the faults. Mode, temperature and fan speed open half-transparent sheets over it: the mode sheet closes once a mode is picked, the others with a tap outside. **System → Panel screen** switches to the fan layout instead, where − and + change the current mode's speed on both fans at once and keep the difference between them, which takes an administrator. The current mode is shown under the speed, and tapping the ring opens the modes. The temperature target has its own screen, one tap away.

The [NSPanel Pro Card](https://github.com/keziksdmitrijs-byte/nspanel-pro-card) can show this panel as its recuperator page (`type: nest_new`). It then takes the card's theme, accent and language, and its leave button goes back to the card's start screen.

The menu has a button to another panel. Choose where it leads with the icon beside it, or under **System → Panel screen**, from a list of panels and dashboard views. The choice stays on the device, or in `input_text.nspanel_home` when that exists, which shares it between devices.

Language, theme and accent are set under **System → Panel screen**, and follow `input_select.nspanel_language`, `input_select.nspanel_theme` and `input_select.nspanel_accent` when those exist. URL parameters: `?lang=lv`, `?theme=dark`, `?accent=teal`, `?home=/path` and `?unit=<entry_id>`. It stays within what an Android 8.1 WebView can run, which `tests/check_panels.js` enforces.

### Access levels

Everyday settings are open to anyone logged in, adjuster settings to administrators, and service settings to administrators who enter the unit's service PIN. The PIN is compared with the one stored in the unit and never kept; access lasts 15 minutes and repeated wrong PINs are locked out. All of this is enforced on the server.

### What to check on a real unit

Verified on firmware 49012: holding registers (function 3) for setpoints, input registers (function 4) for data points, zero-based, and the bit order of the fault words.

Not yet verified:

1. Fan 1 is taken to be supply, fan 2 exhaust.
2. A mode is set by writing `ControlMode = Manual`, then `OperatingMode`; the Schedule button writes `Auto`.
3. The table marks every register as User; the three access levels are this integration's own.

For a NEST nothing is verified on a real unit: that table addresses go on the wire as they are (register 1 at address 1); that current mode 4 is boost, set with coil 5; that the service PIN is entered in holding register 199 and the open access level shows in input register 106; whether settings need the "save to memory" command (coil 51); the clock (registers 100–102 and 104–106, then coil 2). A NEST has no Schedule tab: its ten weekly events and its holidays are plain settings, with the days of the week as a sum (Monday 1 … Sunday 64).

Diagnostics (device page → **Download diagnostics**) leave out addresses and the PIN.

### Development

```bash
pip install -r requirements_test.txt
pytest
python -m tests.simulator --port 5020 --faults
```

`registers_nest.json` (NEST) is generated with `scripts/build_registers_nest.py <table.xlsx>`; `python -m tests.simulator --model nest` pretends to be one. `registers.json` (NEST LS) is generated with `scripts/build_registers.py <workbook.xlsm>`. The workbook is not in the repository, and the script leaves out Bluetooth and Nabto keys, PIN codes, factory records and output overrides.

## License

MIT
