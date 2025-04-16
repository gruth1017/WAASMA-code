# responsible for authentication and verifies who the user is
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from datetime import timedelta
from db_config import get_user_by_username  # you’ll define this
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = get_user_by_username(username)  # your db call
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"msg": "Bad username or password"}), 401

    token = create_access_token(
        identity={"username": user["username"], "role": user["role"]},
        expires_delta=timedelta(hours=1)
    )
    return jsonify(access_token=token), 200
