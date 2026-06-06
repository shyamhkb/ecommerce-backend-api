from flask import Flask, app, jsonify, request
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Product
import os
from models import db, User, Product, Cart, Order
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity
)

load_dotenv()

def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv(
        'SECRET_KEY',
        'dev-secret-key'
    )

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///ecommerce.db'
    )

    app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY',
    'super-secret-jwt-key'
)


    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    JWTManager(app)

    os.makedirs('static/uploads', exist_ok=True)

    with app.app_context():
        db.create_all()

    return app


app = create_app()


@app.route('/')
def home():
    return jsonify({
        "message": "E-Commerce API is running"
    })


@app.route('/api/register', methods=['POST'])
def register():

    data = request.get_json()

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({
            "error": "All fields are required"
        }), 400

    existing_user = User.query.filter(
        (User.username == username) |
        (User.email == email)
    ).first()

    if existing_user:
        return jsonify({
            "error": "User already exists"
        }), 400

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "User registered successfully",
        "user": user.to_dict()
    }), 201


@app.route('/api/login', methods=['POST'])
def login():

    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({
            "error": "User not found"
        }), 404

    if not check_password_hash(user.password_hash, password):
        return jsonify({
            "error": "Invalid password"
        }), 401

    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "user": user.to_dict()
    })


@app.route('/api/products', methods=['GET'])
def get_products():

    products = Product.query.all()

    return jsonify([
        product.to_dict()
        for product in products
    ])


@app.route('/api/products', methods=['POST'])
def add_product():

    data = request.get_json()

    product = Product(
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        stock=data.get('stock', 0)
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        "message": "Product added successfully",
        "product": product.to_dict()
    }), 201


@app.route('/api/profile', methods=['GET'])
@jwt_required()
def profile():

    user_id = get_jwt_identity()

    user = User.query.get(int(user_id))

    return jsonify({
        "message": "Protected route accessed",
        "user": user.to_dict()
    })

@app.route('/api/cart/add', methods=['POST'])
@jwt_required()
def add_to_cart():

    user_id = get_jwt_identity()

    data = request.get_json()

    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    product = Product.query.get(product_id)

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    cart_item = Cart(
        user_id=int(user_id),
        product_id=product_id,
        quantity=quantity
    )

    db.session.add(cart_item)
    db.session.commit()

    return jsonify({
        "message": "Added to cart",
        "cart": cart_item.to_dict()
    }), 201

@app.route('/api/cart', methods=['GET'])
@jwt_required()
def view_cart():

    user_id = get_jwt_identity()

    items = Cart.query.filter_by(
        user_id=int(user_id)
    ).all()

    return jsonify([
        item.to_dict()
        for item in items
    ])

@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():

    user_id = get_jwt_identity()

    cart_items = Cart.query.filter_by(
        user_id=int(user_id)
    ).all()

    if not cart_items:
        return jsonify({
            "error": "Cart is empty"
        }), 400

    total = 0

    for item in cart_items:

        product = Product.query.get(
            item.product_id
        )

        if product:
            total += (
                product.price *
                item.quantity
            )

    order = Order(
        user_id=int(user_id),
        total_amount=total
    )

    db.session.add(order)

    # Cart clear after order
    for item in cart_items:
        db.session.delete(item)

    db.session.commit()

    return jsonify({
        "message": "Order created successfully",
        "order": order.to_dict()
    }), 201

@app.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():

    user_id = get_jwt_identity()

    orders = Order.query.filter_by(
        user_id=int(user_id)
    ).all()

    return jsonify([
        order.to_dict()
        for order in orders
    ])

@app.route('/api/products/<int:id>', methods=['PUT'])
@jwt_required()
def update_product(id):

    product = Product.query.get(id)

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    data = request.get_json()

    product.name = data.get(
        'name',
        product.name
    )

    product.description = data.get(
        'description',
        product.description
    )

    product.price = data.get(
        'price',
        product.price
    )

    product.stock = data.get(
        'stock',
        product.stock
    )

    db.session.commit()

    return jsonify({
        "message": "Product updated successfully",
        "product": product.to_dict()
    })

@app.route('/api/products/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):

    product = Product.query.get(id)

    if not product:
        return jsonify({
            "error": "Product not found"
        }), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({
        "message": "Product deleted successfully"
    })

@app.route('/routes')
def routes():

    route_list = []

    for rule in app.url_map.iter_rules():
        route_list.append({
            "route": str(rule),
            "methods": list(rule.methods)
        })

    return jsonify(route_list)


if __name__ == '__main__':
    app.run(debug=True)