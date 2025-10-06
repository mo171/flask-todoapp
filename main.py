from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import os


app = Flask(__name__)
load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') #Secrate_key
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    todos = db.relationship('Todo', backref='author', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    desc = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"<Todo {self.title}>"

# Landing page - redirects to appropriate page
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('signup'))

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    # If already logged in, redirect to home
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered. Please use a different email.', 'error')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template("signup.html")  # Fixed typo: was "singup.html"

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/home", methods=['GET', 'POST'])
@login_required
def home():
    user=current_user.is_authenticated
    if request.method == "POST":
        title = request.form.get('title', '').strip()
        desc = request.form.get('desc', '').strip()
        
        if not title or not desc:
            flash('Title and description are required.', 'error')
        else:
            todo = Todo(title=title, desc=desc, user_id=current_user.id)
            db.session.add(todo)
            db.session.commit()
            flash('Todo added successfully!', 'success')
        
        return redirect(url_for('home'))
        
    allTodos = Todo.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", allTodos=allTodos, user=user)


@app.route("/delete/<int:sno>")
@login_required
def delete(sno):
    todo_item = Todo.query.filter_by(sno=sno, user_id=current_user.id).first()
    if todo_item:
        db.session.delete(todo_item)
        db.session.commit()
        flash('Todo deleted successfully!', 'success')
    else:
        flash('Todo not found or you do not have permission to delete it.', 'error')
    return redirect(url_for('home'))

@app.route("/update/<int:sno>", methods=['GET', 'POST'])
@login_required
def update(sno):
    todo_item = Todo.query.filter_by(sno=sno, user_id=current_user.id).first()
    
    if not todo_item:
        flash('Todo not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('home'))
    
    if request.method == "POST":
        title = request.form.get('title', '').strip()
        desc = request.form.get('desc', '').strip()
        
        if not title or not desc:
            flash('Title and description are required.', 'error')
        else:
            todo_item.title = title
            todo_item.desc = desc
            db.session.commit()
            flash('Todo updated successfully!', 'success')
            return redirect(url_for('home'))
    
    return render_template("update.html", todo=todo_item)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created!")
    app.run(debug=True, port=8000)