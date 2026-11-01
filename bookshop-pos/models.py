from datetime import datetime, timezone

from extensions import db


def _now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="cashier")
    full_name = db.Column(db.String(120))
    active = db.Column(db.Boolean, nullable=False, default=True)


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120))
    price = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"))
    cashier_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(40), nullable=False, default="PAID")
    created_at = db.Column(db.DateTime, default=_now)

    customer = db.relationship("Customer")
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"))
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)

    book = db.relationship("Book")


class Shift(db.Model):
    __tablename__ = "shifts"

    id = db.Column(db.Integer, primary_key=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    opened_at = db.Column(db.DateTime, default=_now)
    closed_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="OPEN")

    cashier = db.relationship("User")


class Policy(db.Model):
    __tablename__ = "policies"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(60), unique=True, nullable=False)
    value = db.Column(db.String(120))


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(80))
    detail = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=_now)


def get_policy(key, default=None):
    policy = Policy.query.filter_by(key=key).first()
    return policy.value if policy else default


def set_policy(key, value):
    policy = Policy.query.filter_by(key=key).first()
    if policy is None:
        policy = Policy(key=key, value=str(value))
        db.session.add(policy)
    else:
        policy.value = str(value)
    return policy
