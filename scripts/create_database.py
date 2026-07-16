from app.domain.order_model import OrderModel
from app.infrastructure.database import Base, engine


def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_database_tables()
    print("Tabelas criadas com sucesso.")
