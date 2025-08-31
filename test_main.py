import pytest
import logging
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app, Base, get_db, Order, Nomenclature, OrderItem, Client, Category
from datetime import datetime, timedelta, timezone

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.DEBUG)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client_test():
    return TestClient(app)

@pytest.fixture
def client_data():
    """Данные для тестов"""
    db = SessionLocal()

    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.query(Nomenclature).delete()
    db.query(Category).delete()
    db.query(Client).delete()
    db.commit()

    client = Client(name="Test Client", address="123 Test Street")
    db.add(client)
    db.commit()
    db.refresh(client)

    category = Category(name="Test Category")
    db.add(category)
    db.commit()
    db.refresh(category)

    nomenclature = Nomenclature(name="Test Item", price=10.0, quantity=100, category_id=category.id)
    db.add(nomenclature)
    db.commit()
    db.refresh(nomenclature)

    order = Order(client_id=client.id)
    db.add(order)
    db.commit()
    db.refresh(order)

    nomenclature1 = Nomenclature(name="Test Item", price=100.0, quantity=1, category_id=category.id)
    db.add(nomenclature1)
    db.commit()
    db.refresh(nomenclature1)

    nomenclature2 = Nomenclature(name="Test Item", price=1.0, quantity=10, category_id=category.id)
    db.add(nomenclature2)
    db.commit()
    db.refresh(nomenclature2)

    yield client, order, nomenclature, nomenclature1, nomenclature2

    db.close()

def test_add_item_to_order(client_test, client_data):
    client, order, nomenclature, _, _ = client_data

    data = {
        "order_id": order.id,
        "item_id": nomenclature.id,
        "quantity": 2
    }

    response = client_test.post("/add_item_to_order/", json=data)

    assert response.status_code == 200
    assert response.json()["message"] == "Товар добавлен в заказ"

    db = SessionLocal()
    order_item = db.query(OrderItem).filter(OrderItem.order_id == order.id, OrderItem.item_id == nomenclature.id).first()
    assert order_item is not None
    assert order_item.quantity == 2
    db.close()
    print(f"Добавленный товар: {order_item}")
    print("Тест добавления товара в заказ - OK")

def test_get_order(client_test, client_data):
    client, order, nomenclature, _, _ = client_data

    db = SessionLocal()
    order_item = OrderItem(order_id=order.id, item_id=nomenclature.id, quantity=2)
    db.add(order_item)
    db.commit()
    db.close()

    response = client_test.get(f"/order/{order.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == order.id
    assert data["total_price"] == 20.0
    assert len(data["items"]) == 1
    assert data["items"][0]["item_id"] == nomenclature.id
    assert data["items"][0]["quantity"] == 2
    print(f"Информация о заказе: {data}")
    print("Тест получения информации о заказе - OK")

try:
    def test_client_order_summary(client_test, client_data):
        client, order, nomenclature, _, _ = client_data

        db = SessionLocal()
        order_item = OrderItem(order_id=order.id, item_id=nomenclature.id, quantity=2)
        db.add(order_item)
        db.commit()
        db.close()

        response = client_test.get(f"/client_order_summary/{client.id}")

        assert response.status_code == 200
        data = response.json()
        assert data[0]["total"] == 20.0
        print(f"Информация о заказах клиента: {data}")
        print("Тест получения суммы по заказам клиента - OK")
except Exception as e:
    print("Тест получения суммы по заказам клиента - NOT OK")

def test_top5_popular_items(client_test, client_data):
    client, order, _, nomenclature1, nomenclature2 = client_data

    db = SessionLocal()

    order_item1 = OrderItem(order_id=order.id, item_id=nomenclature1.id, quantity=3)
    order_item2 = OrderItem(order_id=order.id, item_id=nomenclature2.id, quantity=2)
    db.add(order_item1)
    db.add(order_item2)
    db.commit()

    order2 = Order(client_id=client.id)
    db.add(order2)
    db.commit()
    db.refresh(order2)
    
    order_item1_2 = OrderItem(order_id=order2.id, item_id=nomenclature1.id, quantity=5)
    order_item2_2 = OrderItem(order_id=order2.id, item_id=nomenclature2.id, quantity=1)
    order.order_date = datetime.now(timezone.utc) - timedelta(days=5)
    order2.order_date = datetime.now(timezone.utc) - timedelta(days=5)
    db.add(order_item1_2)
    db.add(order_item2_2)
    db.commit()

    db.close()

    response = client_test.get("/top5_popular_items/")

    assert response.status_code == 200
    data = response.json()

    print(f"ТОП-5 популярных товаров: {data}")

    assert len(data) == 2
    print("Тест получения ТОП-5 популярных товаров - OK")
