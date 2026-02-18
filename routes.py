from flask import Blueprint, jsonify

api = Blueprint("api", __name__)

@api.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok"})
