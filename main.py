from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, conint
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from datetime import datetime, timedelta, timezone

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    orders = relationship("Order", back_populates="client")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="orders")
    order_date = Column(DateTime, default=datetime.now(timezone.utc))
    total_price = Column(Numeric, default=0)
    items = relationship("OrderItem", back_populates="order")

class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    parent = relationship("Category", remote_side=[id])
    nomenclature = relationship("Nomenclature", back_populates="category")

class Nomenclature(Base):
    __tablename__ = 'nomenclature'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    quantity = Column(Integer)
    price = Column(Numeric)
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", back_populates="nomenclature")

class OrderItem(Base):
    __tablename__ = 'orderitems'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    item_id = Column(Integer, ForeignKey('nomenclature.id'))
    quantity = Column(Integer)
    order = relationship("Order", back_populates="items")
    item = relationship("Nomenclature")

class OrderItemCreate(BaseModel):
    order_id: int
    item_id: int
    quantity: conint(gt=0)


@app.get("/client_order_summary/{client_id}")
def client_order_summary(client_id: int, db: Session = Depends(get_db)):
    """Получение информации о сумме товаров заказанных для каждого клиента"""
    try:
        result = db.query(Client.name, 
                    func.sum(Nomenclature.price * OrderItem.quantity).label("total")).join(Order).join(OrderItem).join(Nomenclature).filter(Client.id == client_id).group_by(Client.id).all()
        if not result:
            raise HTTPException(status_code=404, detail="Заказы не найдены")
    except Exception as e:
        print("Error in client_order_summary")
        result = None
    result_dict = [{"name": name, "total": float(total)} for name, total in result]
    return result_dict

@app.get("/top5_popular_items/")
def top5_popular_items(db: Session = Depends(get_db)):
    """Получение ТОП-5 самых покупаемых товаров за последний месяц"""
    result = db.query(Nomenclature.name,
                  Category.name.label('category_name'),
                  func.sum(OrderItem.quantity).label('total_sold')) \
          .join(OrderItem) \
          .join(Order) \
          .join(Category) \
          .filter(Order.order_date >= datetime.now(timezone.utc) - timedelta(days=30)) \
          .group_by(Nomenclature.id, Category.id) \
          .order_by(func.sum(OrderItem.quantity).desc()) \
          .limit(5).all()
    
    result_dict = [
        {
            "nomenclature_name": row[0] if row[0] is not None else "Unknown",
            "category_name": row[1] if row[1] is not None else "Unknown",
            "total_sold": row[2] if row[2] is not None else 0
        }
        for row in result
    ]
    if not result_dict:
        return []

    return result_dict

@app.get("/orders_by_date/")
def get_orders_sorted_by_date(db: Session = Depends(get_db)):
    """Получение всех заказов, отсортированных по времени заказа (от новых к старым)"""
    try:
        result = db.query(Order).order_by(Order.order_date.desc()).all()
        if not result:
            raise HTTPException(status_code=404, detail="Заказы не найдены")
    except Exception as e:
        print(f"Error in get_orders_sorted_by_date: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении заказов")

    return [
        {
            "order_id": order.id,
            "client_id": order.client_id,
            "order_date": order.order_date,
            "total_price": float(order.total_price),
            "items": [{"item_id": item.item_id, "quantity": item.quantity} for item in order.items]
        }
        for order in result
    ]

@app.post("/add_item_to_order/")
def add_item_to_order(data: OrderItemCreate, db: Session = Depends(get_db)):
    """Добавление товара к заказу и пересчет общей суммы заказа"""
    item = db.query(Nomenclature).filter(Nomenclature.id == data.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")
    if item.quantity < data.quantity:
        raise HTTPException(status_code=400, detail="Недостаточно товара на складе")

    order_item = db.query(OrderItem).filter(
        OrderItem.order_id == data.order_id,
        OrderItem.item_id == data.item_id
    ).first()

    if order_item:
        new_quantity = order_item.quantity + data.quantity
        if item.quantity < new_quantity:
            raise HTTPException(status_code=400, detail="Недостаточно товара на складе для увеличения количества")
        order_item.quantity = new_quantity
    else:
        order_item = OrderItem(order_id=data.order_id, item_id=data.item_id, quantity=data.quantity)
        db.add(order_item)

    item.quantity -= data.quantity
    db.commit()

    order = db.query(Order).filter(Order.id == data.order_id).first()
    if order:
        total_price = sum(
            order_item.quantity * order_item.item.price for order_item in order.items
        )
        order.total_price = total_price
        db.commit()

    return {"message": "Товар добавлен в заказ", "order_id": data.order_id, "item_id": data.item_id, "quantity": data.quantity}

@app.get("/order/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Получение данных о заказе с общей суммой"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.total_price == 0:
        order.total_price = sum(
            order_item.quantity * order_item.item.price for order_item in order.items
        )
        db.commit()

    return {
        "order_id": order.id,
        "client_id": order.client_id,
        "order_date": order.order_date,
        "total_price": order.total_price,
        "items": [{"item_id": item.item_id, "quantity": item.quantity} for item in order.items]
    }

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    app.run(debug=True)
