from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import LoginForm, RegisterForm, CreateListingForm, CommentForm
from flask_gravatar import Gravatar
import stripe
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["USELESS_KEY"]
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
stripe.api_key = os.environ["STRIPE_API_KEY"]

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# CONFIGURE TABLE
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    stripe_account_id = db.Column(db.String(100), nullable=False)
    reviews = relationship("Review", back_populates="review_author")
    products = relationship("Product", back_populates='product_owner')


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(250), unique=True, nullable=False)
    price = db.Column(db.String(250), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    date_posted = db.Column(db.String(250), nullable=False)
    reviews = relationship("Review", back_populates="parent_product")
    product_owner = relationship("User", back_populates='products')


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_product = relationship("Product", back_populates="reviews")
    review_author = relationship("User", back_populates="reviews")
    text = db.Column(db.Text, nullable=False)


db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_products():
    products = Product.query.all()
    return render_template("index.html", all_products=products, current_user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            print(User.query.filter_by(email=form.email.data).first())
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )

        # Strip OnBoard
        response = stripe.Account.create(
                  country="US",
                  type="express",
                  email=form.email.data,
                  capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                  },
                  business_type="individual",
                  business_profile={"url": "google.com"},
                )

        link = stripe.AccountLink.create(
          account=response['id'],
          refresh_url="http://127.0.0.1:5000",
          return_url="http://127.0.0.1:5000",
          type="account_onboarding",
        )
        new_user.stripe_account_id = response['id']
        print(response['id'])
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(link['url'])

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_products'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_products'))


@app.route("/post/<product_owner>/<int:product_id>", methods=["GET", "POST"])
def show_product(product_id, product_owner):
    form = CommentForm()
    requested_product = Product.query.get(product_id)

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_review = Review(
            text=form.comment_text.data,
            review_author=current_user,
            parent_product=requested_product
        )
        db.session.add(new_review)
        db.session.commit()

    return render_template("post.html", product=requested_product, form=form, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
def add_new_listing():
    form = CreateListingForm()
    if form.validate_on_submit():
        new_product = Product(
            title=form.title.data,
            price=form.price.data,
            description=form.description.data,
            stock=form.stock.data,
            img_url=form.img_url.data,
            product_owner=current_user,
            date_posted=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for("get_all_products"))

    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:product_id>", methods=["GET", "POST"])
def edit_listing(product_id):
    product = Product.query.get(product_id)
    edit_form = CreateListingForm(
        title=product.title,
        price=product.price,
        description=product.description,
        stock=product.stock,
        img_url=product.img_url,
        product_owner=current_user,
    )
    if edit_form.validate_on_submit():
        product.title = edit_form.title.data
        product.price = edit_form.price.data
        product.description = edit_form.description.data
        product.stock = edit_form.stock.data
        product.img_url = edit_form.img_url.data
        db.session.commit()
        return redirect(url_for("show_product", product_id=product.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:product_id>")
@admin_only
def delete_post(product_id):
    post_to_delete = Product.query.get(product_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_products'))


@app.route('/create-checkout-session/<product_id>', methods=['GET', 'POST'])
def create_checkout_session(product_id):
    product = Product.query.filter_by(id=product_id).first()
    product_owner = User.query.filter_by(id=product.owner_id).first()
    formatted_price = int(float(product.price) * 100)
    print(product_owner.stripe_account_id)
    print(product_owner.name)
    print(product_owner.email)

    stripe_product = stripe.Product.create(name="Rubber Duck")
    # Create Price
    price_obj = stripe.Price.create(
        unit_amount=formatted_price,
        currency="usd",
        product=stripe_product.id,
    )
    # Create Session and Checkout
    session = stripe.checkout.Session.create(
        line_items=[{
            'price': price_obj.id,
            'quantity': 1,
        }],
        mode='payment',
        success_url='https://example.com/success',
        cancel_url='https://example.com/failure',
        payment_intent_data={
            'application_fee_amount': 123,
            'transfer_data': {
                'destination': product_owner.stripe_account_id,
            },
        },
    )
    print(session)

    return redirect(session.url)


if __name__ == "__main__":
    app.run(debug=True)
