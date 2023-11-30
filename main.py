from flask import Flask, jsonify, request, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'VCNXTruxHj')
db = SQLAlchemy(app)


# Function to generate HATEOAS links for a blog post
def generate_blog_post_links(blog_id, is_author):
    links = [
        {'rel': 'self', 'href': url_for('get_blog_post', blog_id=blog_id, _external=True)},
    ]

    if is_author:
        links.append({'rel': 'update', 'href': url_for('partial_update_blog_post', blog_id=blog_id, _external=True)})
        links.append({'rel': 'delete', 'href': url_for('delete_blog_post', blog_id=blog_id, _external=True)})

    return links



# Function to generate HATEOAS links for the entire blog
def generate_blog_links():
    links = [
        {'rel': 'self', 'href': url_for('get_all_blog_posts', _external=True)},
    ]

    user_id = session.get('user_id')
    if user_id:
        links.append({'rel': 'add', 'method': 'POST', 'href': url_for('create_blog_post', _external=True)})

    return links


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html'), 200


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add a foreign key to link the BlogPost to the User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('blog_posts', lazy=True))


@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Both username and password are required'}), 400

    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        return jsonify({'error': 'Username already exists'}), 400

    new_user = User(username=username)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'})


# Add this route to check if a user is logged in
@app.route('/api/check_login', methods=['GET'])
def check_login():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return jsonify({'user_id': user.id, 'username': user.username})
    else:
        return jsonify({'user_id': None})


# New endpoint for user login
@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # Check if a user is already logged in
        if 'user_id' in session:
            return jsonify({'error': 'Already logged in'}), 400

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            return jsonify({'message': 'Login successful'})

        return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# New endpoint for user logout
@app.route('/api/logout', methods=['GET'])
def logout_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 400

    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'})


@app.route('/api/blog', methods=['POST'])
def create_blog_post():
    try:
        data = request.get_json()
        content = data.get('content')

        # Get the user_id from the session or any other way you manage sessions
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({'error': 'User not logged in'}), 401

        if content is None:
            return jsonify({'error': 'Content is required for a blog post'}), 400

        new_post = BlogPost(author=User.query.get(user_id).username, content=content, user_id=user_id)
        db.session.add(new_post)
        db.session.commit()

        # Debugging Output: Print HATEOAS links
        post_links = generate_blog_post_links(new_post.id, is_author=(new_post.user_id == user_id))
        blog_links = generate_blog_links()
        print(f'HATEOAS Links for the created blog post (ID: {new_post.id}): {post_links}')
        print(f'HATEOAS Links for the entire blog: {blog_links}')

        return jsonify({'id': new_post.id, 'message': 'Blog post created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Endpoint for getting all blog posts with HATEOAS links
@app.route('/api/blog', methods=['GET'])
def get_all_blog_posts():
    blog_posts = BlogPost.query.all()
    posts = []
    for post in blog_posts:
        post_data = {
            'id': post.id,
            'author': post.author,
            'content': post.content,
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'links': generate_blog_post_links(post.id, is_author=(post.user_id == session.get('user_id')))
        }
        posts.append(post_data)

    return jsonify({'posts': posts, 'links': generate_blog_links()})


# Endpoint for getting a specific blog post with HATEOAS links
@app.route('/api/blog/<int:blog_id>', methods=['GET'])
def get_blog_post(blog_id):
    post = BlogPost.query.get(blog_id)
    if post:
        post_data = {
            'id': post.id,
            'author': post.author,
            'content': post.content,
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'links': generate_blog_post_links(blog_id, is_author=(post.user_id == session.get('user_id')))
        }
        return jsonify(post_data)
    else:
        return jsonify({'error': 'Blog post not found'}), 404


@app.route('/api/blog/<int:blog_id>', methods=['DELETE'])
def delete_blog_post(blog_id):
    post = BlogPost.query.get(blog_id)

    if not post:
        return jsonify({'error': 'Blog post not found'}), 404

    if post.user_id != session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify({'message': 'Blog post deleted successfully'})


@app.route('/api/blog/<int:blog_id>', methods=['PATCH'])
def partial_update_blog_post(blog_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    post = BlogPost.query.get(blog_id)
    if not post:
        return jsonify({'error': 'Blog post not found'}), 404

    if post.user_id != session.get('user_id'):
        return jsonify({'error': 'You are not the author of this blog post'}), 403

    data = request.get_json()

    if 'content' in data and data['content']:
        post.content = data['content']

    db.session.commit()

    return jsonify({'message': 'Blog post partially updated successfully'})


# Add this route to get the currently logged-in user information
@app.route('/api/current_user', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return jsonify({'user_id': user.id, 'username': user.username})
    else:
        return jsonify({'user_id': None})


# Run the server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
