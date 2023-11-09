from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
db = SQLAlchemy(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html'), 200


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Endpoint pro vytvoření nového blog postu
@app.route('/api/blog', methods=['POST'])
def create_blog_post():
    data = request.get_json()
    new_post = BlogPost(author=data['author'], content=data['content'])
    db.session.add(new_post)
    db.session.commit()
    return jsonify({'id': new_post.id})


# Endpoint pro získání všech blog postů
@app.route('/api/blog', methods=['GET'])
def get_all_blog_posts():
    blog_posts = BlogPost.query.all()
    posts = []
    for post in blog_posts:
        posts.append({
            'id': post.id,
            'author': post.author,
            'content': post.content,
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify({'posts': posts})


# Endpoint pro získání jednoho konkrétního blog postu podle ID
@app.route('/api/blog/<int:blog_id>', methods=['GET'])
def get_blog_post(blog_id):
    post = BlogPost.query.get(blog_id)
    if post:
        return jsonify({
            'id': post.id,
            'author': post.author,
            'content': post.content,
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({'error': 'Blog post not found'}), 404


# Endpoint pro smazání blog postu podle ID
@app.route('/api/blog/<int:blog_id>', methods=['DELETE'])
def delete_blog_post(blog_id):
    post = BlogPost.query.get(blog_id)
    if post:
        db.session.delete(post)
        db.session.commit()
        return jsonify({'message': 'Blog post deleted successfully'})
    else:
        return jsonify({'error': 'Blog post not found'}), 404


# Endpoint pro částečný update blog postu podle ID
@app.route('/api/blog/<int:blog_id>', methods=['PATCH'])
def partial_update_blog_post(blog_id):
    post = BlogPost.query.get(blog_id)
    if not post:
        return jsonify({'error': 'Blog post not found'}), 404

    data = request.get_json()

    if 'author' in data:
        post.author = data['author']

    if 'content' in data:
        post.content = data['content']

    db.session.commit()

    return jsonify({'message': 'Blog post partially updated successfully'})


# Spustit server
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
