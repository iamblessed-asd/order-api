# Order API (FastAPI + SQLAlchemy + SQLite)

## Запуск проекта

Проект запускается в контейнере Docker. В Dockerfile уже настроена установка зависимостей, запуск тестов и запуск приложения.

### 1. Собрать контейнер
```bash
docker-compose build
```

### 2. Запустить сервис
```bash
docker-compose up
```
#### Или сразу, пропуская первый пункт
```bash
docker-compose up --build
```

### 3. Можно проверить доступность, например, обратившись к документации от FastAPI:
```
http://localhost:8000/docs
```
---

## Структура проекта

- `main.py` — основной файл приложения (FastAPI + SQLAlchemy)
- `test_main.py` — тесты для API (pytest)
- `create_tables.py` — создание таблиц и заполнение тестовыми данными
- `requirements.txt` — зависимости проекта
- `docker-compose.yaml` и `Dockerfile` — конфигурация для контейнера

---

## Описание `main.py`

### Модели (SQLAlchemy)

- **Client** — клиенты  
  `id`, `name`, `address`  

- **Order** — заказы  
  `id`, `client_id`, `order_date`, `total_price`  

- **Category** — категории товаров  
  `id`, `name` (уникальное), `parent_id` (нужен для неограниченной вложенности)  

- **Nomenclature** — товары  
  `id`, `name`, `quantity`, `price`, `category_id`  

- **OrderItem** — связь заказа и товаров  
  `id`, `order_id`, `item_id`, `quantity`  

---

### Эндпоинты

- **`POST /add_item_to_order/`**  
  Добавляет товар в заказ и пересчитывает общую стоимость.

- **`GET /order/{order_id}`**  
  Возвращает заказ: клиент, дата, общая сумма и список товаров.

- **`GET /client_order_summary/{client_id}`**  
  Возвращает сумму заказов клиента.

- **`GET /top5_popular_items/`**  
  Возвращает 5 самых популярных товаров за месяц (по количеству проданных штук).

- **`GET /orders_by_date/`**  
  Возвращает все заказы, отсортированные по дате (от новых к старым).

---

## Описание `test_main.py`

Тесты используют **pytest** и встроенный `TestClient` из FastAPI.

### Фикстуры
- `client_test` — клиент для запросов к API.  
- `client_data` — создаёт тестового клиента, категорию, товары и заказ (очищает базу перед запуском каждого теста).

### Тесты

- **`test_add_item_to_order`**  
  Проверяет, что товар корректно добавляется в заказ через API.

- **`test_get_order`**  
  Проверяет, что заказ возвращается с корректной суммой и списком товаров.

- **`test_client_order_summary`**  
  Проверяет, что для клиента возвращается сумма заказов.

- **`test_top5_popular_items`**  
  Проверяет, что API возвращает корректный список самых популярных товаров.  
  (в тестах выводятся промежуточные результаты: количество категорий, товаров и заказов).

---

## Запуск тестов

При старте контейнера тесты запускаются автоматически (`pytest`).  
Вывод тестов должен быть таким, если всё прошло успешно:

```bash
Тест добавления товара в заказ - OK
order-api-1  | .Информация о заказе: {'order_id': 1, 'client_id': 1, 'order_date': '2025-08-31T12:25:35.071516', 'total_price': 20.0, 'items': [{'item_id': 1, 'quantity': 2}]}
order-api-1  | Тест получения информации о заказе - OK
order-api-1  | .Информация о заказах клиента: [{'name': 'Test Client', 'total': 20.0}]
order-api-1  | Тест получения суммы по заказам клиента - OK
order-api-1  | .ТОП-5 популярных товаров: [{'nomenclature_name': 'Test Item', 'category_name': 'Test Category', 'total_sold': 8}, {'nomenclature_name': 'Test Item', 'category_name': 'Test Category', 'total_sold': 3}]
order-api-1  | Тест получения ТОП-5 популярных товаров - OK
```
