from flask import Flask
from flask_jwt_extended import JWTManager
from config import Config
from models import Book, db, User
from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
jwt = JWTManager(app)

with app.app_context():
    db.create_all()


@app.route('/books', methods=['GET'])
def get_books():

    books = Book.query.all()

    return jsonify([{"id": book.id, "title": book.title, "author": book.author, "published_date": book.published_date} for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):

    book_entity = Book.query.get_or_404(book_id)

    return jsonify(
        {"id": book_entity.id,
         "title": book_entity.title,
         "author": book_entity.author,
         "published_date": book_entity.published_date,
         "user_id": book_entity.user_id}
    ), 200

@app.route('/books', methods=['POST'])
@jwt_required()
def add_book():

    title = request.form.get('title')
    author = request.form.get('author')
    published_date = request.form.get('published_date')
    user_id = request.form.get('user_id')

    if not user_id:
        return {"message": "user_id is required"}, 400

    error_response = checkingEnteredData(title, author, published_date)

    if error_response:
        return jsonify(error_response[0]), error_response[1]

    max_id = db.session.query(db.func.max(Book.id)).scalar()
    next_id = (max_id or 0) + 1

    book_entity = Book(id = next_id,title=title, author=author, published_date=published_date, user_id=user_id)

    db.session.add(book_entity)
    db.session.commit()

    return jsonify({"message": "Book added successfully"}), 201

@app.route('/books/<int:book_id>', methods=['PUT'])
@jwt_required()
def update_book(book_id):

    current_user = get_jwt_identity()
    book_entity = Book.query.get_or_404(book_id)

    title = request.form.get('title')
    author = request.form.get('author')
    published_date = request.form.get('published_date')

    checkingUserAccess(current_user, book_entity.user_id)

    error_response = checkingEnteredData(title, author, published_date)

    if error_response:
        return jsonify(error_response[0]), error_response[1]

    book_entity.title = title if title else book_entity.title
    book_entity.author = author if author else book_entity.author
    book_entity.published_date = published_date if published_date else book_entity.published_date

    db.session.commit()

    return jsonify({"message": "Book updated successfully"}), 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
@jwt_required()
def delete_book(book_id):

    current_user = get_jwt_identity()
    book_entity = Book.query.get_or_404(book_id)

    user_id = request.form.get('user_id')

    checkingUserAccess(current_user, book_entity.user_id)

    db.session.delete(book_entity)
    db.session.commit()

    return jsonify({"message": "Book deleted successfully"}), 200

def checkingEnteredData(title, author, published_date):

    if not title or not author or not published_date:
        return {"message": "Title, author, and published_date are required"}, 400

    if len(title) > 200:
        return {"message": "Title exceeds maximum length"}, 400

    if len(author) > 100:
        return {"message": "Author exceeds maximum length"}, 400

    try:
        datetime.strptime(published_date, '%Y-%m-%d')
    except ValueError:
        return {"message": "Invalid date format. Use YYYY-MM-DD"}, 400


    return None

def checkingUserAccess(user_id, book_user_id):
    if str(book_user_id) != str(user_id):
        return jsonify({"message": "You can't update this book yourself"}), 403

@app.route('/api/register', methods=['POST'])
def register():

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    if len(username) < 3 or len(username) > 50:
        return jsonify({"message": "Username must be between 3 and 50 characters"}), 400

    if len(password) < 6 or len(password) > 100:
        return jsonify({"message": "Password must be between 6 and 100 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 400

    user_entity = User(username=username, password=password)

    db.session.add(user_entity)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@app.route('/api/login', methods=['POST'])
def login():

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"message": "Username and password are required"}), 400

    user_entity = User.query.filter_by(username=username, password=password).first()

    if not user_entity:
        return jsonify({"message": "Invalid credentials"}), 401

    access_token = create_access_token(identity=username)

    return jsonify(access_token=access_token), 200

if __name__ == '__main__':
    app.run(debug=True, port=2454)