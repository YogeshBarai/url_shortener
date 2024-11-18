from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, URL, VisitorCount
import os
from datetime import datetime
import random
import string

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'db', 'shorturl.db')

app = Flask(__name__)

if not os.path.exists(os.path.join(BASE_DIR, 'db')):
    os.makedirs(os.path.join(BASE_DIR, 'db'))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.secret_key = os.urandom(24)

db.init_app(app)
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='sha256')
        
        user = User(username=username, email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully!", "success")
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    urls = URL.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', urls=urls)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize the visitor counter if it doesn't exist
    visitor = VisitorCount.query.first()
    if visitor is None:
        visitor = VisitorCount(count=0)
        db.session.add(visitor)
        db.session.commit()

    # Increment the visitor count
    visitor.count += 1
    db.session.commit()

    # Get the total number of URLs shortened
    total_urls = URL.query.count()

    if request.method == 'POST':
        long_url = request.form['long_url']
        short_url = ''.join(random.choices(string.ascii_letters + string.digits, k=6))

        # Check if the user is logged in
        if current_user.is_authenticated:
            # Save with associated user ID
            url = URL(long_url=long_url, short_url=short_url, user_id=current_user.id)
        else:
            # Save without a user ID for anonymous users
            url = URL(long_url=long_url, short_url=short_url)

        db.session.add(url)
        db.session.commit()

        flash(f"Short URL: {request.host_url}{short_url}", "success")

    return render_template('index.html', visitor_count=visitor.count, total_urls=total_urls)


@app.route('/<short_url>')
def redirect_url(short_url):
    url = URL.query.filter_by(short_url=short_url).first_or_404()
    return redirect(url.long_url)


@app.context_processor
def inject_year():
    return {'current_year': datetime.now().year}


if __name__ == '__main__':
    app.run(debug=True)