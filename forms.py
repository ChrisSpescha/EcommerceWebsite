from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


# WTForm
class CreateListingForm(FlaskForm):
    title = StringField("Listing Title", validators=[DataRequired()])
    price = StringField("Price", validators=[DataRequired()])
    stock = StringField("Amount Available for Sale", validators=[DataRequired()])
    img_url = StringField("Product Image URL", validators=[DataRequired(), URL()])
    description = CKEditorField("Product Description", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")


class ReviewForm(FlaskForm):
    review_text = CKEditorField("Leave a Review!", validators=[DataRequired()])
    submit = SubmitField("Submit Review")


class MessageForm(FlaskForm):
    message = StringField("Compose Message", validators=[DataRequired()])
    submit = SubmitField("Send")
