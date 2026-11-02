# ДЗ_6 · Tool Call Assertion Suite

Власна копія кіта L07: **10 сценаріїв, 32 очікування мока**, три власні сценарії
**S6, S7, S8**. S1O і S3B - розділення сценаріїв кіта, не додаткові власні роботи.
Документи українською, діалоги англійською для стабільного префікса промпту.

## Результат перевірки

На чистій локальній копії, стенд `325e2dd`, OpenAI `gpt-5-mini-2025-08-07`:

| Команда | Результат |
|---|---|
| `docker compose run --rm -T eval --gate daily` | 7 завершених кроків, без ERROR; baseline 4/4 PASS; D12, D29, D11 виявлено |
| `docker compose run --rm -T eval --condition baseline` | baseline усіх 10 сценаріїв PASS, без ERROR |

У фактичних термінальних командах додано `-p l07`, щоб користуватися одним
локальним мок-контейнером. Вони запускалися послідовно. Повний release з п'ятьма
повторами кожної умови ще не виконано для всіх нових сценаріїв.
Фінальні сирі дані: `reports/hw6-v3/final-verification-timeout60/`.
Аудит: `evidence/hw6-final-audit.json`; пояснення: `evidence/hw6-results.md`.
Проміжні FAIL та транспортні помилки залишено, успіхи їх не стирають.

## Документи

- [Заповнена Policy](tool-call-testing-policy.md) · [PDF](tool-call-testing-policy.pdf).
- [Порожня переносима форма](tool-call-testing-policy-template.md) · [PDF](tool-call-testing-policy-template.pdf).
- [Історичний лабораторний звіт](evidence/l07-laboratory-results.md): 45 кроків до HW6.
- [Прогноз до лабораторної](evidence/l07-forecast.md). Числового власного USD-прогнозу до запусків не було; довідкові ≈3x із курсу не видаються за нього.

## Сценарії

| ID | Перевірка | gate | runs |
|---|---|---|---|
| S1 | правильний рахунок після write; явна згода, живий крок 4; D12 | daily | 1 |
| S1O | eligibility перед write: патерн порядку | release | 5 |
| S2 | анафора обирає TX-0202, не TX-0204 | release | 5 |
| S3 | контракт результату eligibility; D29 | daily | 1 |
| S3B | прострочений спір не відкривається; D29 | release | 5 |
| S4 | повтор наміру залишає рівно один спір | daily | 1 |
| S5 | мінімум кешу від другого виклику; D28 | release | 5 |
| S6 | валюта спору відповідає транзакції; D11 | daily | 1 |
| S7 | ліміти замість історії платежів; D13 | release | 5 |
| S8 | без згоди немає спору й надсилання виписки | release | 5 |

Кожен сценарій має `dimension`, `level`, `gate`, `runs`, профіль `clean`.
Дефект задається лише через settings запиту. Усі assertions читають спани,
контракт або стан, жодна не читає текст відповіді.

## Локальний запуск із чистого клону

Потрібні Docker Desktop / Compose та окремий локальний стенд
[paypilot-stand-shared](https://github.com/sergeytkachenko/paypilot-stand-shared)
на коміті `325e2dd3b7f653d5ceae842516528a71d27603fc` або суміснішому.
Не запускайте проти спільного стенду: ранер скидає тестову базу.
Ключ OpenAI задається в локальному `.env` **стенду**, не цього репозиторію.
Приклад для наявних папок курсу на macOS; назву клону можна змінити:

```bash
course_dir="$HOME/Downloads/4 AI Quality Engineering"
kit_dir="$course_dir/l07"
cd "$kit_dir"
docker compose -p l07 run --rm -T --entrypoint python eval build_mock.py </dev/null
docker compose -p l07 up -d llm-mock </dev/null
```

Після зміни сценаріїв перебудуйте очікування та застосуйте їх:

```bash
curl -fsS -X PUT http://localhost:1080/mockserver/expectation \
  -H 'Content-Type: application/json' \
  --data-binary @mock/expectations.json -o /dev/null
```

Один раз запустіть наявний стенд через override. Це відтворює стенд, але ще
не викликає модель. Абсолютний `L07_DIR` дозволяє розташувати клон будь-де:

```bash
cd "$course_dir/paypilot-stand-shared"
PROFILE=clean DEFECTS="" L07_PROVIDER=openai L07_DIR="$kit_dir" \
  docker compose -f docker-compose.yml \
  -f "$kit_dir/mock/stand.override.yml" \
  up -d --build --force-recreate stand </dev/null
```

Перед тестом дочекайтеся `status: ok`, `provider: openai`, `profile: clean`
на `http://localhost:8000/health` та 32 активних очікувань на MockServer :1080.
MockServer має таймаут 60000 мс: стандартні 20000 мс спричиняли локальні 502
із ReadTimeoutException. Це не виправлення і не заміна API-ключа.

**Наступні команди викликають платну модель.** `-T` та `</dev/null` запобігають
поглинанню решти вставленого блоку Docker-контейнером.

```bash
cd "$kit_dir"
docker compose -p l07 run --rm -T eval --gate daily </dev/null
docker compose -p l07 run --rm -T eval --condition baseline </dev/null
```

Release запускайте окремо, коли потрібна частотна перевірка. З поточним каталогом
це 45 живих кроків; це не 45 API-запитів, бо крок може потребувати кількох викликів.

```bash
docker compose -p l07 run --rm -T eval --gate release </dev/null
```

Для збереження результатів використовуйте нову папку кожної спроби, `--json`,
журнал термінала, каталог сценаріїв, версію ранера, трейс та стан перед наступним
reset. Поступове збереження пише JSON після завершеної умови; всередині умови
з кількома runs незавершені результати можуть залишитися тільки в журналі.
Для надійних контрольних точок запускайте по одному прогону в окремій папці.
Не робіть автоматичний retry всього діалогу після транспортного збою.

## Офлайн-перевірка без моделі

```bash
python3 scripts/audit_hw6.py
python3 scripts/audit_l07.py
```

Перший аудит перевіряє фінальні 17 кроків, каталог і зіставлення спанів;
state-verdicts є збереженими результатами нативного ранера, а фінальний snapshot
таблиці належить лише останньому сценарію серії. Другий аудит відтворює лише
45 історичних лабораторних кроків за замороженими сценаріями й ранером.
Він не застосовує нові assertions до старих результатів.

`run_step.py` повертає помилку процесу при ERROR, але не при assertion FAIL.
CI має читати `runs[].passed`: baseline FAIL блокує, очікуваний дефектний FAIL
підтверджує чутливість тесту. Порожній/неповний JSON не означає PASS.

## Походження і зміни

Основа: [paypilot-l07-eval](https://github.com/sergeytkachenko/paypilot-l07-eval),
коміт `77614ceac81d06941773839ffabfdd3c7f617551`.
Локальні зміни: S6-S8, поділ порядку/стану і контракту/поведінки, явна згода S1,
метадані, таймаут проксі, поступове збереження, Policy та аудити.
Ключі й `.env` не комітити. Попередні репозиторії ДЗ не змінювати.
Для здачі потрібен окремий публічний репозиторій ДЗ_6, гілка `main`, його URL у LMS.
