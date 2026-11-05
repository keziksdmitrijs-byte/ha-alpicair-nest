# AlpicAir NEST for Home Assistant

[Русский](#русский) · [English](#english)

## Русский

Интеграция для рекуператоров **AlpicAir NEST** с контроллером ES1125. Подключается по Modbus TCP напрямую, без облака. Панель настроек, данных, расписания, сервиса и ошибок встроена в интеграцию и появляется в боковом меню Home Assistant.

> **Статус: чтение проверено на настоящей установке** (прошивка 49012, таблица регистров 48012): поиск в сети, все показания и настройки. Управление режимами на настоящей установке ещё не проверялось, см. раздел [«Что проверить на установке»](#что-проверить-на-установке). Сервисные настройки меняйте осторожно.

### Установка

Через HACS: **HACS → Integrations → ⋮ → Custom repositories**, адрес этого репозитория, категория **Integration**. Затем установите **AlpicAir NEST** и перезапустите Home Assistant.

Вручную: скопируйте папку `custom_components/alpicair_nest` в `config/custom_components/` и перезапустите Home Assistant.

На установке должен быть включён Modbus TCP, порт по умолчанию 502.

### Подключение

**Настройки → Устройства и службы → Добавить интеграцию → AlpicAir NEST**, затем на выбор:

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

На квадратном экране (SONOFF NSPanel Pro, 480×480) панель сама переходит на отдельную раскладку: всё основное на одном экране, внизу вкладки со значками, у чисел кнопки − и +. Весь экран масштабируется под плотность пикселей устройства. Файл панели рассчитан на старый WebView Android 8.1.

Откройте на панели адрес `/alpicair-nest`. Если в Home Assistant есть `input_select.nspanel_language`, язык берётся из него. Параметры адреса: `?lang=lv` задаёт язык, `?compact=1` включает раскладку на любом экране, `?compact=0` выключает.

Названия регистров существуют на русском и английском. На латышском переведены сама панель и режимы, а названия настроек показываются по-английски.

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

Если что-то не сходится, приложите диагностику: страница устройства → **Скачать диагностику**. Адреса и PIN в неё не попадают.

### Разработка

```bash
pip install -r requirements_test.txt
pytest

# симулятор установки на порту 5020
python -m tests.simulator --port 5020 --faults
```

`custom_components/alpicair_nest/registers.json` создаётся из таблицы производителя командой `scripts/build_registers.py <файл.xlsm>`. Сама таблица в репозитории не хранится. Ключи Bluetooth и Nabto, PIN-коды, заводские записи и принудительное управление выходами скрипт отбрасывает.

## English

Local Modbus TCP integration for **AlpicAir NEST** heat-recovery units with the ES1125 controller, with a built-in sidebar panel for settings, schedule, data, service and faults. No cloud.

> **Status: reading is verified on a real unit** (firmware 49012, register table 48012): network search, all readings and settings. Mode control has not been tried on a real unit yet, see [What to check on a real unit](#what-to-check-on-a-real-unit).

### Install

With HACS: add this repository under **HACS → Integrations → ⋮ → Custom repositories** with category **Integration**, install **AlpicAir NEST** and restart Home Assistant. Or copy `custom_components/alpicair_nest` into `config/custom_components/`.

Modbus TCP must be enabled on the unit (port 502 by default).

### Set up

**Settings → Devices & services → Add integration → AlpicAir NEST**, then either enter the IP address or let it search the local networks. The search only reads, and recognises a unit by its registers.

### Square wall panels

On a square screen such as the SONOFF NSPanel Pro (480×480) the panel switches to its own layout, with the essentials on one screen, icon tabs at the bottom and − / + buttons on numbers. It scales to the device's pixel density and stays within what an Android 8.1 WebView can run. Open `/alpicair-nest` on the device. The language follows `input_select.nspanel_language` when that exists; `?lang=lv` sets it, and `?compact=1` or `?compact=0` forces the layout on or off.

### Access levels

Everyday settings are open to anyone logged in, adjuster settings to administrators, and service settings to administrators who enter the unit's service PIN. The PIN is compared with the one stored in the unit and never kept; access lasts 15 minutes and repeated wrong PINs are locked out. All of this is enforced on the server.

### What to check on a real unit

Verified on firmware 49012: holding registers (function 3) for setpoints, input registers (function 4) for data points, zero-based, and the bit order of the fault words.

Not yet verified:

1. Fan 1 is taken to be supply, fan 2 exhaust.
2. A mode is set by writing `ControlMode = Manual`, then `OperatingMode`; the Schedule button writes `Auto`.
3. The table marks every register as User; the three access levels are this integration's own.

Diagnostics (device page → **Download diagnostics**) leave out addresses and the PIN.

### Development

```bash
pip install -r requirements_test.txt
pytest
python -m tests.simulator --port 5020 --faults
```

`registers.json` is generated with `scripts/build_registers.py <workbook.xlsm>`. The workbook is not in the repository, and the script leaves out Bluetooth and Nabto keys, PIN codes, factory records and output overrides.

## License

MIT
