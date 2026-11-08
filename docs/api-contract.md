# HTTP-контракт EasyTv

Источник истины: роуты `backend/easytv/api/`, DTO в `schemas.py`, перечисления в `core/models.py`. FastAPI публикует `/openapi.json` и `/docs`. Фронтенд вручную повторяет контракт в `frontend/src/types.ts` и `api.ts`; генерации клиента сейчас нет.

## Общие правила

- JSON использует camelCase, внутренние Python-модели — snake_case. Не менять сериализацию без синхронного изменения клиента.
- Nullable-поля передаются как `null`; даты в JSON — строки. Не подменять неизвестные позицию/длительность нулём.
- Ошибка предметной области: `{ "detail": "описание" }`. Валидация FastAPI может вернуть массив в `detail`; клиент обрабатывает оба формата.
- Коды: 404 — объект не найден; 409 — видео не готово или текущее состояние не позволяет выполнить перемотку; 415 — неподдерживаемый формат; 422 — некорректные данные, недоступный ТВ или поток; 502 — ошибка команды ТВ/каталога. Остальные предметные ошибки по умолчанию дают 400.
- DELETE и команды без результата возвращают 204 без JSON. Фоновая загрузка возвращает 202 и объект Video, а не готовый файл.

## Маршруты

Все пути в таблице начинаются с `/api`.

| Метод и путь | Вход / результат |
| --- | --- |
| GET `/tvs` | Список Tv |
| POST `/tvs/refresh` | Обновлённый список Tv |
| POST `/tvs` | `{address}` → Tv |
| GET, DELETE `/tvs/{id}` | Tv / удаление известного устройства |
| GET `/tvs/{id}/playback` | Playback |
| POST `/tvs/{id}/play` | `{videoId}` → Playback |
| POST `/tvs/{id}/pause`, `/resume`, `/stop` | Команда, 204 |
| POST `/tvs/{id}/seek` | `{positionS}` или `{offsetS}` → 204 |
| POST `/tvs/{id}/play-stream` | StreamRef + `title`, необязательная `translation` → Playback |
| GET `/videos` | Список Video |
| POST `/videos/upload` | multipart с полем `file` → Video, 201 |
| POST `/videos/youtube` | `{url}` → Video, 202 |
| POST `/videos/direct` | `{url}` с прямой HTTP(S)-ссылкой на видеофайл → Video, 202 |
| DELETE `/videos/{id}` | Удаление, 204 |
| GET `/catalog/search?q=...` | Список CatalogTitle |
| GET `/catalog/collections` | Список Collection |
| GET `/catalog/collections/{id}?page=1` | Список CatalogTitle |
| GET `/catalog/titles/{id}` | TitleDetails |
| GET `/catalog/titles/{id}/episodes` | Список Episode |
| GET `/catalog/titles/{id}/variants?episode=0` | Список Variant |
| POST `/catalog/resolve` | StreamRef + необязательная `translation` → `{url, provider, quality}` |
| POST `/catalog/download` | StreamRef + `title` → Video, 202 |
| GET `/cinema` | Список SavedTitle |
| POST `/cinema` | `{titleId}` → SavedTitle, 201 |
| DELETE `/cinema/{titleId}` | Удаление, 204 |

Перемотка доступна в состояниях `playing` и `paused`. Передайте одно целое число в секундах. `positionS` задаёт неотрицательную позицию от начала видео, а `offsetS` задаёт смещение от текущей позиции ТВ и может быть отрицательным. Сервер ограничивает результат началом и, если известна длительность, концом видео. Для смещения при неизвестной позиции ТВ возвращается 409. Отказ ТВ выполнить команду возвращается как 502.

Для `/videos/direct` некорректный адрес сразу даёт 400. Тип файла определяется по `Content-Type` итогового ответа после редиректов. Для бинарной отдачи без конкретного типа используется расширение из `Content-Disposition` или URL. Если по ссылке приходит страница, плейлист либо ответ с ошибкой, загрузка переходит в `failed`, а причина записывается в `error`.

## Основные модели

- Tv: `id`, `name`, `ip`, `manufacturer`, `model`, `online`, `lastSeen`.
- Video: `id`, `title`, `source`, `status`, `progress`, `size`, `error`, `originUrl`, `createdAt`. Источники: `upload`, `youtube`, `animego`, `direct`; состояния: `pending`, `downloading`, `ready`, `failed`. Прогресс — доля от 0 до 1.
- Playback: `state`, `videoId`, `positionS`, `durationS`, `title`, `stream`. Состояния: `playing`, `paused`, `stopped`, `transitioning`, `no_media`, `unknown`. Времена — секунды, могут быть неизвестны.
- StreamRef: `titleId`, `episode` (0 для фильма), `translationId`, `provider` (по умолчанию `auto`).
- SavedTitle: метаданные тайтла, озвучка, `lastEpisode`, `watched`, даты добавления и обновления. Сейчас это общая запись; `watched` означает запущенные серии, не достоверно досмотренные.

Полные поля каталожных моделей и их nullable-типы следует читать в DTO и `types.ts`, а не восстанавливать по экрану.

## Медиапоток и изменения

`/media/...` отдаёт локальные файлы, `/stream/...` проксирует внешний источник. Это двоичные HTTP-ответы, не JSON API. Сохранять GET/HEAD, Range, частичные ответы 206, обработку недопустимых диапазонов и необходимые DLNA-заголовки согласно реализации и тестам. Для потоков использовать URL, возвращённый resolve, не собирать внешнюю CDN-ссылку на клиенте.

При изменении API вместе обновлять серверный DTO/роут, клиентский тип/вызов и сценарные тесты. Проверять статусы, ошибки, пустые ответы, состояния загрузки и nullable-поля. Не считать TypeScript-приведение `as T` проверкой JSON во время выполнения.
