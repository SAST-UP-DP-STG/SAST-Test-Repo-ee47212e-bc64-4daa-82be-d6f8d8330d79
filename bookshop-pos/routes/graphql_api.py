from ariadne import MutationType, QueryType, gql, graphql_sync, make_executable_schema
from ariadne.explorer import ExplorerGraphiQL
from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, Book

type_defs = gql(
    """
    type Book {
        id: Int!
        isbn: String!
        title: String!
        author: String
        price: Float!
        stock: Int!
    }

    type Query {
        catalog: [Book!]!
        book(id: Int!): Book
    }

    type Mutation {
        setPrice(bookId: Int!, price: Float!): Book
        setStock(bookId: Int!, stock: Int!): Book
    }
    """
)

query = QueryType()
mutation = MutationType()


@query.field("catalog")
def resolve_catalog(obj, info):
    return Book.query.order_by(Book.title).all()


@query.field("book")
def resolve_book(obj, info, id):
    return Book.query.get(id)


@mutation.field("setPrice")
def resolve_set_price(obj, info, bookId, price):
    book = Book.query.get(bookId)
    if book is None:
        return None
    book.price = float(price)
    db.session.add(
        AuditLog(action="GQL_SET_PRICE", detail=f"book={bookId} price={book.price}")
    )
    db.session.commit()
    return book


@mutation.field("setStock")
def resolve_set_stock(obj, info, bookId, stock):
    book = Book.query.get(bookId)
    if book is None:
        return None
    book.stock = int(stock)
    db.session.add(
        AuditLog(action="GQL_SET_STOCK", detail=f"book={bookId} stock={book.stock}")
    )
    db.session.commit()
    return book


schema = make_executable_schema(type_defs, query, mutation)
explorer_html = ExplorerGraphiQL().html(None)

bp = Blueprint("graphql_api", __name__)


@bp.route("/graphql", methods=["GET"])
def graphql_explorer():
    return explorer_html, 200


@bp.route("/graphql", methods=["POST"])
def graphql_server():
    data = request.get_json(silent=True) or {}
    success, result = graphql_sync(schema, data, context_value={"request": request})
    status_code = 200 if success else 400
    return jsonify(result), status_code
