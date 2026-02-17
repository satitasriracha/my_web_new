# myapp/context_processors.py


def user_context(request):
    return {
        "user_name": request.session.get("user_name"),
        "user_id": request.session.get("user_id"),
        "is_logged_in": request.session.get("is_logged_in", False),
    }

# myapp/context_processors.py
def customer_context(request):
    return {
        "customer_name": request.session.get("customer_name", None)
    }

def cart_count(request):
    cart = request.session.get("cart", {})
    return {
        "cart_count": sum(cart.values())
    }
