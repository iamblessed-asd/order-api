from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, conint
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    orders = relationship("Order", back_populates="client")

class Order(Base):
    __tablename__ = 'order'
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="orders")
    order_date = Column(DateTime, default=datetime.now(datetime.timezone.utc))

class Category(Base):
    __tablename__ = 'category'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    parent = relationship("Category", remote_side=[id])

class Nomenclature(Base):
    __tablename__ = 'nomenclature'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    quantity = Column(Integer)
    price = Column(Numeric)
    category_id = Column(Integer, ForeignKey('category.id'))

class OrderItem(Base):
    __tablename__ = 'orderitem'
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('order.id'), index=True)
    item_id = Column(Integer, ForeignKey('nomenclature.id'), index=True)
    quantity = Column(Integer)

class OrderItemCreate(BaseModel):
    order_id: int
    item_id: int
    quantity: conint(gt=0)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/add_item_to_order/")
def add_item_to_order(data: OrderItemCreate, db: Session = Depends(get_db)):
    """Добавление товара к заказу"""
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
    return {"message": "Товар добавлен в заказ", "order_id": data.order_id, "item_id": data.item_id, "quantity": data.quantity}
