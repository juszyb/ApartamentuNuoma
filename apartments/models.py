import enum

from apartments import db, login_manager
from flask_login import UserMixin, current_user
from sqlalchemy.orm import relationship
from datetime import datetime
from functools import wraps
from flask import abort

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

def owner_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        result = PropertyOwner.query.with_entities(PropertyOwner.fk_user_id)
        for r in result:
            if current_user.id == r.fk_user_id:
                return f(*args, **kwargs)
            else:
                return abort(403)
    return decorated_function

class User(UserMixin, db.Model):
    __tablename__ = "naudotojas"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.DateTime, nullable=True)
    phone_number = db.Column(db.String(100), nullable=True)
    property_owner = relationship("PropertyOwner", back_populates="user")
    tenant = relationship("Tenant", back_populates="user")


class PropertyOwner(UserMixin, db.Model):
    __tablename__ = "nuomotojas"
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    company_code = db.Column(db.Integer, nullable=False, unique=True)
    apartment = relationship("Apartment", back_populates="property_owner")
    user = relationship("User", back_populates="property_owner")
    fk_user_id = db.Column(db.Integer, db.ForeignKey("naudotojas.id"))

class Apartment(db.Model):
    __tablename__ = "apartamentai"
    id = db.Column(db.Integer, primary_key=True)
    apartment_name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(100), nullable=False, unique=True)
    phone_number = db.Column(db.String(100), nullable=False, unique=True)
    stars = db.Column(db.Integer, nullable=True)
    img_url = db.Column(db.String(250), nullable=False)
    latitude = db.Column(db.Float(20), nullable=False)
    longitude = db.Column(db.Float(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    feedback = relationship("Feedback", back_populates="apartment")
    property_owner = relationship("PropertyOwner", back_populates="apartment")
    room = relationship("Room", back_populates="apartment")
    fk_property_owner_id = db.Column(db.Integer, db.ForeignKey("nuomotojas.id"))



class Tenant(db.Model):
    __tablename__ = "nuomininkas"
    id = db.Column(db.Integer, primary_key=True)
    user = relationship("User", back_populates="tenant")
    feedback = relationship("Feedback", back_populates="tenant")
    bill = relationship("Bill", back_populates="tenant")
    booking = relationship("Booking", back_populates="tenant")
    fk_user_id = db.Column(db.Integer, db.ForeignKey("naudotojas.id"))


room_reservation = db.Table(
    'kambariu_rezervacija',
    db.Column('room_id', db.Integer, db.ForeignKey('kambarys.id')),
    db.Column('booking_id', db.Integer, db.ForeignKey('uzsakymas.id')),
)

class Room(db.Model):
    __tablename__ = "kambarys"
    id = db.Column(db.Integer, primary_key=True)
    free_room = db.Column(db.Boolean, unique=False, default=True)
    text = db.Column(db.Text, nullable=False)
    room_number = db.Column(db.Integer, nullable=False)
    room_fees = db.Column(db.Float(20), nullable=False)
    breakfast_fees = db.Column(db.Float(20), nullable=False)
    other_fees = db.Column(db.Float(20), nullable=False)
    room_type = relationship("RoomType", back_populates="room")
    apartment = relationship("Apartment", back_populates="room")
    booking = relationship("Booking", secondary=room_reservation, back_populates="room")
    fk_apartment_id = db.Column(db.Integer, db.ForeignKey("apartamentai.id"))
    fk_room_type_id = db.Column(db.Integer, db.ForeignKey("kambario_tipas.id"))


class RoomType(db.Model):
    __tablename__ = "kambario_tipas"
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), nullable=False)
    price_for_night = db.Column(db.Float(20), nullable=False)
    number_of_beds = db.Column(db.Integer)
    room = relationship("Room", back_populates="room_type")

class Feedback(db.Model):
    __tablename__ = "atsiliepimas"
    id = db.Column(db.Integer, primary_key=True)
    overall_assessment = db.Column(db.Integer, nullable=False)
    staff_assessment = db.Column(db.Integer, nullable=False)
    comfort_assessment = db.Column(db.Integer, nullable=False)
    cleanliness_assessment = db.Column(db.Integer, nullable=False)
    place_assessment = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.strftime(datetime.today(), "%Y-%m-%d"))
    apartment = relationship("Apartment", back_populates="feedback")
    tenant = relationship("Tenant", back_populates="feedback")
    booking = relationship("Booking", back_populates="feedback")
    fk_apartment_id = db.Column(db.Integer, db.ForeignKey("apartamentai.id"))
    fk_tenant_id = db.Column(db.Integer, db.ForeignKey("nuomininkas.id"))
    fk_booking_id = db.Column(db.Integer, db.ForeignKey("uzsakymas.id"))


class BookingStatus(enum.Enum):
    finished = "finished"
    cancelled = "cancelled"
    ongoing = "ongoing"

class Booking(db.Model):
    __tablename__ = "uzsakymas"
    id = db.Column(db.Integer, primary_key=True)
    arrival_date = db.Column(db.DateTime, nullable=False,)
    departure_date = db.Column(db.DateTime, nullable=False)
    num_of_persons = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(BookingStatus), nullable=False)
    tenant = relationship("Tenant", back_populates="booking")
    bill = relationship("Bill", back_populates="booking")
    room = relationship("Room", secondary=room_reservation, back_populates="booking")
    feedback = relationship("Feedback", back_populates="booking")
    fk_tenant_id = db.Column(db.Integer, db.ForeignKey("nuomininkas.id"))
    fk_bill_id = db.Column(db.Integer, db.ForeignKey("saskaita.id"))


class Bill(db.Model):
    __tablename__ = "saskaita"
    id = db.Column(db.Integer, primary_key=True)
    full_price = db.Column(db.Float(20), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.strftime(datetime.today(), "%Y-%m-%d"))
    tenant = relationship("Tenant", back_populates="bill")
    booking = relationship("Booking", back_populates="bill")
    payment = relationship("Payment", back_populates="bill")
    fk_tenant_id = db.Column(db.Integer, db.ForeignKey("nuomininkas.id"))

class Payment(db.Model):
    __tablename__ = "apmokejimas"
    id = db.Column(db.Integer, primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.strftime(datetime.today(), "%Y-%m-%d"))
    bill = relationship("Bill", back_populates="payment")
    fk_bill_id = db.Column(db.Integer, db.ForeignKey("saskaita.id"))
