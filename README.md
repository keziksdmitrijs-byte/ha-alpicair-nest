# AlpicAir NEST for Home Assistant

[Русский](#русский) · [English](#english)

## Русский

Интеграция для рекуператоров **AlpicAir NEST** с контроллером ES1125. Подключается по Modbus TCP напрямую, без облака. Панель настроек, данных, расписания, сервиса и ошибок встроена в интеграцию и появляется в боковом меню Home Assistant.

> **Статус: проверено только на симуляторе.** Интеграция написана по таблице регистров версии 48012 и ещё не запускалась на настоящей установке. Что нужно сверить, перечислено в разделе [«Что проверить на установке»](#что-проверить-на-установке). Пока это не сделано, начинайте с чтения данных и меняйте сервисные настройки осторожно.

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

Таблица не отвечает на всё, и эти решения приняты по косвенным признакам:

1. **Типы регистров.** Setpoints читаются как holding (функция 3), Datapoints как input (функция 4), адресация с нуля.
2. **Порядок битов в словах ошибок.** Принято, что последний пункт списка в таблице это бит 0. Если сообщения об ошибках не совпадают с дисплеем установки, порядок обратный; сырые значения показаны на вкладке «Ошибки».
3. **Вентиляторы.** Принято, что вентилятор 1 приточный, вентилятор 2 вытяжной.
4. **Управление режимом.** Чтобы режим не перезаписывался расписанием, сначала ставится `ControlMode = Manual`, затем `OperatingMode`. Кнопка «По расписанию» возвращает `Auto`.
5. **Уровни доступа.** В таблице у всех регистров указан уровень User, разделение на три уровня сделано здесь.

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

> **Status: tested on a simulator only.** It was written from register table version 48012 and has not yet run against a real unit. See [What to check on a real unit](#what-to-check-on-a-real-unit).

### Install

With HACS: add this repository under **HACS → Integrations → ⋮ → Custom repositories** with category **Integration**, install **AlpicAir NEST** and restart Home Assistant. Or copy `custom_components/alpicair_nest` into `config/custom_components/`.

Modbus TCP must be enabled on the unit (port 502 by default).

### Set up

**Settings → Devices & services → Add integration → AlpicAir NEST**, then either enter the IP address or let it search the local networks. The search only reads, and recognises a unit by its registers.

### Access levels

Everyday settings are open to anyone logged in, adjuster settings to administrators, and service settings to administrators who enter the unit's service PIN. The PIN is compared with the one stored in the unit and never kept; access lasts 15 minutes and repeated wrong PINs are locked out. All of this is enforced on the server.

### What to check on a real unit

1. Setpoints are read as holding registers (function 3), data points as input registers (function 4), zero-based.
2. Fault words: the last item of the table's list is taken to be bit 0. Raw words are on the Faults tab to compare with the unit's display.
3. Fan 1 is taken to be supply, fan 2 exhaust.
4. A mode is set by writing `ControlMode = Manual`, then `OperatingMode`; the Schedule button writes `Auto`.
5. The table marks every register as User; the three access levels are this integration's own.

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
