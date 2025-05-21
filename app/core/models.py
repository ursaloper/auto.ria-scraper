"""
Модели данных для работы с базой данных.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Car(Base):
    """
    Модель для хранения информации об автомобилях.

    Attributes:
        id (int): Уникальный идентификатор записи
        url (str): URL страницы автомобиля
        title (str): Заголовок объявления
        price_usd (int): Цена в USD
        odometer (int): Пробег в километрах
        username (str): Имя продавца
        phone_number (str): Номер телефона продавца
        image_url (str): URL основного изображения
        images_count (int): Количество изображений
        car_number (str): Номер автомобиля
        car_vin (str): VIN-код автомобиля
        datetime_found (datetime): Дата и время сохранения в базу
    """

    __tablename__ = "cars"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    price_usd = Column(Integer, nullable=False)
    odometer = Column(Integer, nullable=False)  # Хранится в километрах
    username = Column(String, nullable=False)
    phone_number = Column(
        String, nullable=False
    )  # Храним как строку для сохранения формата +38063...
    image_url = Column(String)
    images_count = Column(Integer, default=0)
    car_number = Column(String)
    car_vin = Column(String, index=True)
    datetime_found = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Создаем индексы для часто используемых полей
    __table_args__ = (
        UniqueConstraint("url", name="uq_car_url"),
        UniqueConstraint("car_vin", name="uq_car_vin"),
    )

    def __repr__(self):
        """Строковое представление модели."""
        return f"<Car(id={self.id}, title='{self.title}', vin='{self.car_vin}')>"
