"""
Data models for working with the database.

This module contains SQLAlchemy ORM model definitions for storing
and managing data collected by the auto.ria.com scraper. The main model is Car,
which represents a car from the auto.ria.com website.

Classes:
    Base: Base class for all SQLAlchemy ORM models.
    Car: Model for storing car information.
"""

from datetime import datetime

from sqlalchemy import String  # type: ignore
from sqlalchemy import Column, DateTime, Integer, UniqueConstraint  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore

Base = declarative_base()


class Car(Base):
    """
    Model for storing car information.

    Contains all necessary information about each car collected by the scraper
    from the AutoRia website. Includes unique URL, price information, seller contact data,
    mileage data and car identification information.

    Attributes:
        id (int): Unique record identifier in the database.
        url (str): Car page URL on AutoRia website. Indexed and must be unique.
        title (str): Ad title, usually contains brand, model and year.
        price_usd (int): Car price in US dollars.
        odometer (int): Car mileage in kilometers.
        username (str): Seller name or company name.
        phone_number (str): Seller phone number in international format.
        image_url (str): Main car image URL.
        images_count (int): Total number of images in the ad.
        car_number (str): Car license plate number, if available.
        car_vin (str): Car VIN code for identification. Indexed.
        datetime_found (datetime): Date and time when the ad was found and saved.

    Note:
        Unique constraints are created for URL and VIN code to prevent duplication.
        The url and car_vin fields are indexed to speed up searches.
    """

    __tablename__ = "cars"

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    price_usd = Column(Integer, nullable=False)
    odometer = Column(Integer, nullable=True)  # Stored in kilometers
    username = Column(String, nullable=False)
    phone_number = Column(
        String, nullable=False
    )  # Store as string to preserve format +380...
    image_url = Column(String)
    images_count = Column(Integer, default=0)
    car_number = Column(String)
    car_vin = Column(String, index=True)
    datetime_found = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Create indexes for frequently used fields
    __table_args__ = (
        UniqueConstraint("url", name="uq_car_url"),
        UniqueConstraint("car_vin", name="uq_car_vin"),
    )

    def __repr__(self):
        """
        String representation of the model.

        Returns:
            str: String containing car ID, title and VIN.
        """
        return f"<Car(id={self.id}, title='{self.title}', vin='{self.car_vin}')>"
