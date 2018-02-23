import sys
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import datetime

Base = declarative_base()


class User(UserMixin, Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    restaurants = relationship('Restaurant', backref='user', lazy=True)

    def get_id(self):
        return self.id


class Restaurant(Base):
    __tablename__ = 'restaurant'
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    menu_item = relationship('MenuItem', cascade='all, delete-orphan')
    user_id = Column(Integer, ForeignKey(User.id),
                     nullable=False)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id
        }


class MenuItem(Base):
    __tablename__ = 'menu_item'
    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    course = Column(String(250))
    description = Column(String(250))
    price = Column(String(8))
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)
    user_id = Column(Integer, nullable=False)

    @property
    def serialize(self):
        return {
            'name': self.name,
            'id': self.id,
            'course': self.course,
            'description': self.description,
            'price': self.price
        }
if __name__ == '__main__':
    engine = create_engine('sqlite:///restaurantmenu.db')
    Base.metadata.create_all(engine)
