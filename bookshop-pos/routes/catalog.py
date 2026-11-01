from flask import Blueprint, render_template

from models import Book
from auth import current_user, require_auth

bp = Blueprint("catalog", __name__)
bp.before_request(require_auth)


@bp.route("/catalog")
def catalog():
    books = Book.query.order_by(Book.title).all()
    return render_template("catalog.html", user=current_user(), books=books)
