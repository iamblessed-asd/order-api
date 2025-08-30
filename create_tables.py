from sqlalchemy import create_engine
from main import Base, SessionLocal, Nomenclature

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

Base.metadata.create_all(bind=engine)

print("Таблицы успешно созданы")

db = SessionLocal()

nomenclatures = [
    Nomenclature(name="Товар 1", quantity=100, price=20.5, category_id=1),
    Nomenclature(name="Товар 2", quantity=150, price=30.0, category_id=2),
    Nomenclature(name="Товар 3", quantity=50, price=10.0, category_id=1),
]

db.add_all(nomenclatures)
db.commit()
db.close()

print("Тестовые данные добавлены")