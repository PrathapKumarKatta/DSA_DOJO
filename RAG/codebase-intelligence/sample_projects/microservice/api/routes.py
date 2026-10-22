from typing import Dict
from auth.service import authenticate_user, generate_jwt_token, hash_password
from payments.processor import payment_processor

# Mock in-memory database of registered users
USERS_DATABASE: Dict[str, dict] = {
    "admin@company.com": {
        "id": "usr_001",
        "email": "admin@company.com",
        "password_hash": hash_password("AdminPass123!"),
    }
}


def handle_login_request(payload: dict) -> dict:
    """
    Handles API request for user login flow.
    Validates credentials and returns JWT token.
    """
    email = payload.get("email")
    password = payload.get("password")

    user = authenticate_user(email, password, USERS_DATABASE)
    if not user:
        return {"error": "Invalid credentials", "status": 401}

    token = generate_jwt_token(user["id"], user["email"])
    return {"token": token, "status": 200}


def handle_register_request(payload: dict) -> dict:
    """
    Handles user registration request.
    Hashes password and saves new user record.
    """
    email = payload.get("email")
    password = payload.get("password")

    if email in USERS_DATABASE:
        return {"error": "User already exists", "status": 400}

    new_user = {
        "id": f"usr_{len(USERS_DATABASE) + 1:03d}",
        "email": email,
        "password_hash": hash_password(password),
    }
    USERS_DATABASE[email] = new_user
    return {"user_id": new_user["id"], "email": email, "status": 201}


def process_payment_request(payload: dict) -> dict:
    """
    Handles API request for customer credit card billing.
    """
    customer_id = payload.get("customer_id")
    amount = payload.get("amount", 0)

    try:
        result = payment_processor.charge_card(customer_id, amount)
        return {"result": result, "status": 200}
    except Exception as e:
        return {"error": str(e), "status": 400}
