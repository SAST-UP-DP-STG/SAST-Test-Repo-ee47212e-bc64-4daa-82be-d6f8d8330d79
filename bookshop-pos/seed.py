from extensions import db, bcrypt
from models import Book, Customer, Order, OrderItem, User, set_policy


def seed_data():
    db.drop_all()
    db.create_all()

    manager = User(
        username="manager",
        password_hash=bcrypt.generate_password_hash("manager123").decode("utf-8"),
        role="manager",
        full_name="Dana Reyes",
        active=True,
    )
    cashier = User(
        username="cashier",
        password_hash=bcrypt.generate_password_hash("cashier123").decode("utf-8"),
        role="cashier",
        full_name="Sam Patel",
        active=True,
    )
    db.session.add_all([manager, cashier])

    books = [
        Book(isbn="9780000000001", title="The Midnight Library", author="Matt Haig", price=16.99, stock=12),
        Book(isbn="9780000000002", title="Atomic Habits", author="James Clear", price=21.50, stock=8),
        Book(isbn="9780000000003", title="Project Hail Mary", author="Andy Weir", price=18.00, stock=3),
        Book(isbn="9780000000004", title="Educated", author="Tara Westover", price=14.25, stock=20),
        Book(isbn="9780000000005", title="The Silent Patient", author="Alex Michaelides", price=12.99, stock=2),
    ]
    db.session.add_all(books)

    customers = [
        Customer(name="Laura Bennett", email="laura.bennett@example.com", phone="555-0101"),
        Customer(name="Marcus Hill", email="marcus.hill@example.com", phone="555-0102"),
        Customer(name="Priya Nair", email="priya.nair@example.com", phone="555-0103"),
    ]
    db.session.add_all(customers)
    db.session.flush()

    set_policy("refundApprovalRequired", "true")
    set_policy("maxDiscountPercent", "20")

    orders = [
        Order(customer_id=customers[0].id, cashier_id=cashier.id, subtotal=16.99, discount_percent=0, total=16.99, status="PAID"),
        Order(customer_id=customers[1].id, cashier_id=cashier.id, subtotal=43.00, discount_percent=0, total=43.00, status="PAID"),
        Order(customer_id=customers[2].id, cashier_id=cashier.id, subtotal=18.00, discount_percent=0, total=18.00, status="PAID"),
    ]
    db.session.add_all(orders)
    db.session.flush()

    db.session.add_all(
        [
            OrderItem(order_id=orders[0].id, book_id=books[0].id, quantity=1, unit_price=16.99),
            OrderItem(order_id=orders[1].id, book_id=books[1].id, quantity=2, unit_price=21.50),
            OrderItem(order_id=orders[2].id, book_id=books[2].id, quantity=1, unit_price=18.00),
        ]
    )
    db.session.commit()
