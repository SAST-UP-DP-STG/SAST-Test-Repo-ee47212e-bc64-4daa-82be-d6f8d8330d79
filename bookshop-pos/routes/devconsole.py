from flask import Blueprint, jsonify, request

bp = Blueprint("devconsole", __name__)


@bp.route("/console/eval", methods=["POST"])
def console_eval():
    data = request.get_json(silent=True) or {}
    expr = str(data.get("expr", ""))
    result = eval(expr)
    return jsonify({"expr": expr, "result": repr(result)})
