# JoomPulse Creative Intelligence

Платформа автоматического анализа рекламных креативов из Meta Ads: забирает креативы и метрики из рекламного кабинета, дожидается статистической значимости, силами LLM раскладывает каждый креатив на нормированные параметры (боль / концепция / объект / CTA), и присылает в Telegram вердикт по каждому креативу — что выключать, что масштабировать.

Цель — собрать структурированный датасет «параметры креатива → перформанс», чтобы на его основе искать паттерны лучших креативов и на следующем шаге генерировать новые гипотезы автоматически.

---

## 1. Объём MVP

В первую итерацию входит только ingest + анализ + нотификации. Генерация креативов — следующая фаза, заложена в архитектуре, но не реализуется на MVP.

### In scope

1. **Meta Ads ingest.** Подключение к рекламному кабинету через официальный Meta Marketing API. Инкрементальная синхронизация ad accounts → campaigns → ad sets → ads → creatives, plus insights (impressions, clicks, spend, CPM, CTR, CPA, ROAS, etc.) в виде time-series снапшотов.
2. **Performance verdict.** Как только креатив набирает ≥ 1000 impressions (порог конфигурируем, см. §7), он автоматически ставится в очередь на оценку. LLM сравнивает метрики с бенчмарками кабинета (его же аккаунта, скользящее окно 30 дней) и классифицирует как `best_performer` / `low_performer` / `neutral`, пишет короткий вердикт на русском.
3. **Creative decomposition.** Для каждого нового уникального креатива вытягиваем бинарный ассет (картинка / видео), раскладываем по нормированной таксономии:
   - `pain` — боль / триггер
   - `concept` — формат / концепция
   - `object` — главный объект в кадре
   - `cta` — призыв к действию

   Таксономия управляемая (controlled vocabulary, см. §6), LLM обязан выбирать значения из словаря и помечать новые кандидаты в бакет `other` для ручной разметки.
4. **Telegram digest.** Мгновенные алерты по критичным вердиктам (low/best performer) + ежедневный сводный дайджест.

### Out of scope (фаза 2+)

- Веб-UI / дашборд (архитектурно заложен, API готов)
- Генерация креативов (image / video)
- A/B рекомендации и авто-применение в Meta
- Мульти-кабинет с ролями

---

## 2. Архитектура

```mermaid
flowchart LR
    subgraph EXT["External"]
        META["Meta Marketing API<br/>(Ads + Insights + Assets)"]
        CLAUDE["Anthropic Claude API<br/>opus-4-7 / sonnet-4-6 / haiku-4-5"]
        TG["Telegram Bot API"]
    end

    subgraph SCHED["Scheduler"]
        BEAT["Celery Beat<br/>cron-like triggers"]
    end

    subgraph BROKER["Broker & cache"]
        REDIS[("Redis<br/>broker + cache + rate-limit")]
    end

    subgraph WORKERS["Celery workers (разные очереди)"]
        WFETCH["queue: fetch<br/>MetaFetcher"]
        WAI["queue: ai<br/>CreativeDecomposer<br/>PerformanceAnalyzer"]
        WNOTIFY["queue: notify<br/>TelegramNotifier"]
    end

    subgraph APP["Application layer"]
        API["FastAPI<br/>REST /admin /health /webhooks"]
        BOT["aiogram 3<br/>Telegram Bot"]
    end

    subgraph DATA["Data layer"]
        PG[("PostgreSQL 16<br/>+ pgvector<br/>core domain + embeddings")]
        S3[("S3 / MinIO<br/>creative assets")]
    end

    BEAT -->|enqueue| REDIS
    REDIS --> WFETCH
    REDIS --> WAI
    REDIS --> WNOTIFY

    WFETCH -->|pull ads, insights,<br/>asset URLs| META
    WFETCH -->|upsert| PG
    WFETCH -->|download binary| S3
    WFETCH -->|enqueue analysis jobs| REDIS

    WAI -->|read asset| S3
    WAI -->|read metrics+taxonomy| PG
    WAI -->|vision + text| CLAUDE
    WAI -->|write analysis & verdict| PG
    WAI -->|enqueue notification| REDIS

    WNOTIFY -->|read pending| PG
    WNOTIFY -->|sendMessage| TG

    BOT <-->|long poll / webhook| TG
    BOT -->|CRUD, ack| PG

    API -->|CRUD| PG
    API -->|presign URLs| S3
    API -->|manual trigger| REDIS

    USER(["Маркетолог / админ"]) --> API
    USER <--> BOT
```

### Компоненты и зоны ответственности

| Компонент | Ответственность |
|---|---|
| **Celery Beat** | Плановые запуски: `fetch_ads` каждые 15 мин, `recompute_benchmarks` раз в час, `daily_digest` в 10:00. |
| **MetaFetcher worker** | Идемпотентный ingest: ad accounts → campaigns → ads → creatives → insights. Инкремент по `updated_time`. Скачивает новые ассеты в S3. Ставит задачи на декомпозицию и, если порог пройден, на performance-анализ. |
| **CreativeDecomposer worker** | Берёт ассет из S3 (для видео — sampling кадров через `ffmpeg`, 1–2 fps, батчами по 15 кадров в один запрос к Claude Vision), промптит Claude с принудительным выводом из таксономии, пишет `creative_analysis`. |
| **PerformanceAnalyzer worker** | Считает относительные метрики (CTR/CPM/CPA в перцентилях против скользящего окна кабинета), отдаёт их + топ-метрики креатива в Claude, получает короткий вердикт + категорию. |
| **TelegramNotifier worker** | Шлёт алерты в заданный чат; батчит в дайджест; ведёт `notification_log` для дедупликации. |
| **FastAPI** | Админ-API: CRUD подключений к Meta, ручные триггеры ingest/re-analysis, просмотр таксономии, health/ready, webhooks (Meta system notifications в будущем). |
| **aiogram 3 bot** | Прямые команды: `/status`, `/creative <id>`, `/digest`, `/disable <id>` (в будущем будет пушить в Meta). |
| **PostgreSQL + pgvector** | Реляционная модель домена + эмбеддинги текстового описания креатива для поиска похожих. |
| **S3 / MinIO** | Бинарники ассетов + извлечённые кадры видео. |
| **Redis** | Брокер Celery, кеш бенчмарков, token-bucket для Meta API rate limits. |

---

## 3. Технологический стек

Стек подобран по трём критериям: (1) зрелость и активный maintenance на апрель 2026, (2) первый класс async-поддержки, (3) минимум «склейки» с Meta SDK и Claude SDK.

### Core

| Слой | Выбор | Почему |
|---|---|---|
| Язык | **Python 3.12** | Официальные SDK Meta и Anthropic — Python-first; весь ML/AI экосистема. |
| Web framework | **FastAPI** | Async, Pydantic v2, OpenAPI из коробки. |
| Telegram | **aiogram 3** | Полностью async с дня один, Production/Stable на апрель 2026, типизированный роутинг. |
| Task queue | **Celery 5 + Celery Beat** | Зрелость, chains/retries/rate-limit, лучший выбор когда есть несколько разнородных пайплайнов. Альтернатива **ARQ** рассмотрена и отклонена: меньше фич (нет chains, беднее scheduler), при росте нагрузки потребует миграции. |
| Broker | **Redis 7** | Одновременно broker + кеш + rate-limit bucket → меньше инфраструктурных компонент. |
| БД | **PostgreSQL 16** + `pgvector` | Реляционная модель с time-series insights; pgvector даст семантический поиск похожих креативов без отдельного vector DB. |
| ORM | **SQLAlchemy 2.0 (async)** + **Alembic** | Стандарт де-факто, хорошо работает с asyncpg. |
| Object storage | **MinIO** (локально) / **S3** (прод) | S3 API совместимость, `aioboto3`. |
| LLM | **Anthropic Claude API** | `claude-opus-4-7` — декомпозиция креативов (vision + сложные суждения); `claude-sonnet-4-6` — performance verdict (дешевле, достаточно умный); `claude-haiku-4-5` — быстрая классификация для bulk. Обязательно **prompt caching** на системный промпт + таксономию (экономия ~80% токенов). |
| Видео | **ffmpeg** (CLI) | Семплинг кадров 1–2 fps, батч по 15 кадров в один vision-запрос — подтверждённый паттерн. |
| Meta Ads | **facebook-business 25.0.0** | Официальный Meta Marketing SDK, актуальная версия на март 2026. |

### Dev & Ops

| Слой | Выбор |
|---|---|
| Контейнеры | **Docker** + **docker-compose** (dev), single-host docker compose → Kubernetes (прод, фаза 2) |
| Config | **pydantic-settings** + `.env` / секреты через окружение |
| Миграции | **Alembic** |
| Логи | **structlog** (JSON), ship в Loki |
| Метрики | **prometheus-client** на всех сервисах |
| Ошибки | **Sentry** |
| Тесты | **pytest** + **pytest-asyncio**, VCR для Meta, response-mocker для Claude |
| Lint / type | **ruff**, **mypy --strict**, **pre-commit** |
| CI | **GitHub Actions**: ruff + mypy + pytest + docker build |
| Секреты в репо | **не допускаются**; `.env.example` + GitHub Actions secrets |

---

## 4. Структура репозитория

```
.
├── README.md
├── pyproject.toml             # poetry / uv, все deps и конфиги инструментов
├── .env.example
├── docker-compose.yml         # postgres, redis, minio, api, worker, beat, bot
├── Dockerfile
├── alembic.ini
├── migrations/                # Alembic
├── src/
│   └── joompulse/
│       ├── __init__.py
│       ├── config.py          # pydantic-settings
│       ├── logging.py
│       ├── db/
│       │   ├── base.py        # async engine, session factory
│       │   └── models/        # SQLAlchemy модели (см. §5)
│       ├── storage/
│       │   └── s3.py          # aioboto3 wrapper
│       ├── meta/
│       │   ├── client.py      # обёртка над facebook_business
│       │   ├── fetcher.py     # ingest-пайплайн
│       │   └── rate_limit.py  # token bucket через Redis
│       ├── ai/
│       │   ├── client.py      # anthropic async client + prompt caching
│       │   ├── taxonomy.py    # загрузка/валидация словаря
│       │   ├── decomposer.py  # vision-декомпозиция креатива
│       │   ├── analyzer.py    # performance verdict
│       │   └── video.py       # ffmpeg frame sampling
│       ├── tasks/
│       │   ├── celery_app.py
│       │   ├── schedule.py    # Beat schedule
│       │   ├── fetch.py       # queue=fetch
│       │   ├── analyze.py     # queue=ai
│       │   └── notify.py      # queue=notify
│       ├── bot/
│       │   ├── main.py        # aiogram entrypoint
│       │   ├── handlers/
│       │   └── keyboards.py
│       ├── api/
│       │   ├── main.py        # FastAPI entrypoint
│       │   ├── deps.py
│       │   └── routers/
│       └── domain/
│           ├── benchmarks.py  # скользящее окно per-account
│           └── verdict.py     # бизнес-логика классификации
├── taxonomy/
│   ├── pain.yaml
│   ├── concept.yaml
│   ├── object.yaml
│   └── cta.yaml
├── prompts/
│   ├── decompose.md
│   ├── analyze.md
│   └── system.md
└── tests/
    ├── unit/
    └── integration/
```

---

## 5. Модель данных (основное)

Only ключевые таблицы, подробности — в `migrations/`.

- `ad_account` — подключение к Meta (ID, токен в зашифрованном виде, статус синка).
- `campaign`, `ad_set`, `ad` — иерархия Meta.
- `creative` — уникальный креатив, дедуплицируется по `meta_creative_id` и hash бинарника (один креатив может быть в N объявлениях).
- `creative_asset` — ссылка на S3, тип (image/video), probe-метаданные (длительность, resolution).
- `metric_snapshot` — time-series: `(ad_id, captured_at, impressions, clicks, spend, ctr, cpm, cpa, roas, ...)`. Партиционирование по `captured_at` (месяц).
- `taxonomy_term` — словарь: `(dimension, code, label_ru, label_en, description, is_active)`.
- `creative_analysis` — результат декомпозиции: FK на `creative`, массивы `pain_codes[]`, `concept_codes[]`, `object_codes[]`, `cta_codes[]`, `raw_json` (полный ответ модели), `embedding vector(1024)` для поиска похожих, `model_version`.
- `performance_verdict` — `(creative_id, ad_id, captured_at, verdict enum, score, rationale_md, model_version)`.
- `notification_log` — идемпотентность уведомлений `(entity_type, entity_id, kind, sent_at)`.

---

## 6. Таксономия и нормализация

Это критичный элемент — без контролируемого словаря данные станут шумом.

1. **Словари** лежат в `taxonomy/*.yaml`, версионируются в git. На старте — seed от маркетинга (~20–40 терминов на измерение).
2. **Загрузка** в `taxonomy_term` при деплое (Alembic data migration или отдельный CLI `joompulse taxonomy sync`).
3. **Decomposer prompt** включает весь словарь (через prompt caching → один раз в сессию) и требует JSON-ответ с валидацией:
   - `pain_codes`: ≥1 значение из словаря `pain` ∪ `{"other"}`
   - `other_suggestion`: строка, если был выбран `other` (кандидат в словарь)
4. **Review loop.** Раз в неделю админ смотрит кандидатов в `other`, либо добавляет в словарь, либо мержит в существующий код. Старые анализы переразмечаются ретро-таском.
5. **Embedding.** Параллельно пишем `embedding` от short-description креатива — для семантического поиска даже когда таксономия ещё не покрывает кейс.

---

## 7. Пайплайны и пороги

| Триггер | Частота | Действие |
|---|---|---|
| `fetch_ads` (Beat) | каждые 15 мин | Ingest Meta → upsert → enqueue `decompose` для новых creative, `analyze_performance` для креативов, перешагнувших порог |
| `decompose_creative(creative_id)` | по событию | Vision-декомпозиция, запись в `creative_analysis` |
| `analyze_performance(ad_id)` | по событию | Условие входа: `impressions ≥ IMPRESSIONS_THRESHOLD` (default 1000) **и** креатив ещё не получал вердикт за последние `REANALYZE_COOLDOWN_H` (default 48) часов |
| `recompute_benchmarks` (Beat) | каждый час | Пересчёт перцентилей CTR/CPM/CPA per-account за скользящие 30 дней |
| `notify_verdict(verdict_id)` | по событию | Мгновенный алерт если `verdict in {best_performer, low_performer}` |
| `daily_digest` (Beat) | 10:00 | Сводка: новые вердикты, топ-5 best / bottom-5 low за 24ч |

Пороги и cooldown'ы — в `config.py`, все конфигурируемы через env.

---

## 8. Конфигурация

`.env.example`:

```ini
# App
APP_ENV=dev
LOG_LEVEL=INFO

# Postgres
POSTGRES_DSN=postgresql+asyncpg://joompulse:joompulse@postgres:5432/joompulse

# Redis
REDIS_URL=redis://redis:6379/0

# S3 / MinIO
S3_ENDPOINT=http://minio:9000
S3_BUCKET=joompulse-assets
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin

# Meta
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_AD_ACCOUNT_IDS=act_xxx,act_yyy

# Anthropic
ANTHROPIC_API_KEY=
CLAUDE_MODEL_DECOMPOSE=claude-opus-4-7
CLAUDE_MODEL_ANALYZE=claude-sonnet-4-6
CLAUDE_MODEL_FAST=claude-haiku-4-5

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALERT_CHAT_ID=
TELEGRAM_DIGEST_CHAT_ID=

# Thresholds
IMPRESSIONS_THRESHOLD=1000
REANALYZE_COOLDOWN_H=48
BENCHMARK_WINDOW_DAYS=30
VIDEO_SAMPLE_FPS=1
VIDEO_FRAMES_PER_REQUEST=15
```

---

## 9. Локальный запуск

```bash
# 1. Поднять зависимости + сервисы
cp .env.example .env
# заполнить секреты
docker compose up -d postgres redis minio
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m joompulse.taxonomy sync

# 2. Запустить всё
docker compose up -d api worker-fetch worker-ai worker-notify beat bot

# 3. Smoke test
curl http://localhost:8000/health
docker compose logs -f beat worker-fetch
```

---

## 10. Безопасность

- Meta access token хранится в `ad_account` в **зашифрованном виде** (Fernet, ключ из env `ENCRYPTION_KEY`). В логах — только последние 4 символа.
- Telegram chat ID верифицируется whitelist'ом.
- Все внешние API-вызовы идут через retry с exponential backoff и ограничены token-bucket'ом в Redis (Meta — 200 call/hour per app по умолчанию).
- S3 bucket приватный, доступ через presigned URL на TTL 15 мин.
- Секреты — только через env, `.env` в `.gitignore`.

---

## 11. Дорожная карта

| Фаза | Скоуп |
|---|---|
| **0. Setup** (эта ветка) | README, скелет репо, docker-compose, пустые миграции |
| **1. Ingest** | Meta SDK client, инкрементальный sync, S3 ассеты |
| **2. Decomposer** | Таксономия, vision-декомпозиция (image → video) |
| **3. Performance** | Бенчмарки, verdict, Telegram alerts + digest |
| **4. Dashboard** | React + Vite + shadcn/ui, explore + паттерны |
| **5. Generate** | Гипотезы креативов на основе победителей, генерация image/video, A/B в Meta |

---

## 12. Итоговый промпт на следующий шаг разработки

> Ты — tech lead проекта JoomPulse Creative Intelligence. Репозиторий пустой, ветка `claude/creative-analysis-platform-oTGbi`. Используя архитектуру, стек и структуру из `README.md`, засетапь каркас: `pyproject.toml` (uv), `docker-compose.yml` (postgres-16, redis-7, minio, api, worker-fetch, worker-ai, worker-notify, beat, bot), `Dockerfile` (multi-stage), `.env.example`, `alembic.ini` + базовую миграцию со всеми таблицами из §5, пустые модули по структуре §4, `src/joompulse/config.py` с pydantic-settings, `src/joompulse/tasks/celery_app.py` с тремя очередями (fetch/ai/notify) и Beat-расписанием из §7, заглушки ручек FastAPI `/health` и `/ready`, CI-воркфлоу `.github/workflows/ci.yml` (ruff + mypy + pytest + docker build), `pre-commit` конфиг, `taxonomy/*.yaml` со seed-словарями по 15–20 терминов на измерение. Всё должно запускаться по инструкции §9 и показывать зелёный health. Не реализуй бизнес-логику — только каркас, который коллеги начнут наполнять параллельно.

---

## License

Proprietary — JoomPulse internal.
