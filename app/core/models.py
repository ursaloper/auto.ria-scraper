"""
Модели данных для работы с базой данных.

Этот модуль содержит определения ORM-моделей SQLAlchemy для хранения
и управления данными, собранными скрапером auto.ria.com. Основная модель - Car,
которая представляет автомобиль с сайта auto.ria.com.

Classes:
    Base: Базовый класс для всех ORM-моделей SQLAlchemy.
    Car: Модель для хранения информации об автомобилях.
"""

from datetime import datetime

from sqlalchemy import String  # type: ignore
from sqlalchemy import (Column, DateTime, Integer,  # type: ignore
                        UniqueConstraint)
from sqlalchemy.ext.declarative import declarative_base  # type: ignore

Base = declarative_base()


class Car(Base):
    """
    Модель для хранения информации об автомобилях.

    Содержит всю необходимую информацию о каждом автомобиле, собранную скрапером
    с сайта AutoRia. Включает уникальный URL, информацию о ценах, контактные данные
    продавца, данные о пробеге и идентификационную информацию автомобиля.

    Attributes:
        id (int): Уникальный идентификатор записи в базе данных.
        url (str): URL страницы автомобиля на сайте AutoRia. Индексируется и должен быть уникальным.
        title (str): Заголовок объявления, обычно содержит марку, модель и год выпуска.
        price_usd (int): Цена автомобиля в долларах США.
        odometer (int): Пробег автомобиля в километрах.
        username (str): Имя продавца или название компании.
        phone_number (str): Номер телефона продавца в международном формате.
        image_url (str): URL основного изображения автомобиля.
        images_count (int): Общее количество изображений в объявлении.
        car_number (str): Государственный регистрационный номер автомобиля, если доступен.
        car_vin (str): VIN-код автомобиля для его идентификации. Индексируется.
        datetime_found (datetime): Дата и время, когда объявление было найдено и сохранено.

    Note:
        Созданы уникальные ограничения для URL и VIN-кода для предотвращения дублирования.
        Поля url и car_vin индексируются для ускорения поиска.
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
        """
        Строковое представление модели.

        Returns:
            str: Строка, содержащая ID, заголовок и VIN автомобиля.
        """
        return f"<Car(id={self.id}, title='{self.title}', vin='{self.car_vin}')>"
