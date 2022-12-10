from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, SubmitField, PasswordField, SelectField, DateField, IntegerField
from wtforms.validators import DataRequired, URL, EqualTo, Email, ValidationError, NumberRange
from flask_ckeditor import CKEditorField
from apartments.models import User

# Naudotojo registracijos forma
class UserRegistrationForm(FlaskForm):
    name = StringField("Vardas", validators=[DataRequired()])
    last_name = StringField("Pavardė", validators=[DataRequired()])
    username = StringField("Prisijungimo vardas", validators=[DataRequired()])
    email = StringField("El. paštas", validators=[DataRequired(), Email()])
    password = PasswordField("Slaptažodis", validators=[DataRequired()])
    confirm_password = PasswordField("Pakartoti slaptažodį", validators=[DataRequired(), EqualTo('password')])
    birth_date = DateField("Gimimo data", validators=[])
    phone_number = IntegerField("Telefono numeris", validators=[])
    submit = SubmitField("Registruotis")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class UserLoginForm(FlaskForm):
    username = StringField("Prisijungimo vardas", validators=[DataRequired()])
    password = PasswordField("Slaptažodis", validators=[DataRequired()])
    submit = SubmitField("Prisijungti")

# Naudotojo registracijos forma
class UpdateProfileForm(FlaskForm):
    name = StringField("Vardas", validators=[DataRequired()])
    last_name = StringField("Pavardė", validators=[DataRequired()])
    username = StringField("Prisijungimo vardas", validators=[DataRequired()])
    email = StringField("El. paštas", validators=[DataRequired(), Email()])
    birth_date = DateField("Gimimo data", validators=[])
    phone_number = StringField("Telefono numeris", validators=[])
    submit = SubmitField("Išsaugoti")

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

#Nuomotojo registracijos forma
class VendorRegistrationForm(FlaskForm):
    name = StringField("Vardas", validators=[DataRequired()])
    last_name = StringField("Pavardė", validators=[DataRequired()])
    username = StringField("Prisijungimo vardas", validators=[DataRequired()])
    email = StringField("El. paštas", validators=[DataRequired()])
    password = PasswordField("Slaptažodis", validators=[DataRequired()])
    confirm_password = PasswordField("Pakartoti slaptažodį", validators=[DataRequired(), EqualTo('password')])
    phone_number = StringField("Telefono numeris", validators=[])
    birth_date = DateField("Gimimo data", validators=[])
    company_name = StringField("Įmonės pavadinimas", validators=[DataRequired()])
    company_code = StringField("Įmonės kodas", validators=[DataRequired()])
    submit = SubmitField("Registruotis")

# Užsakymo forma
class BookingForm(FlaskForm):
    arrival_date = DateField('Atvykimo data', validators=[DataRequired()])
    departure_date = DateField('Išvykimo data', validators=[DataRequired()])
    people_nr = IntegerField('Žmonių skaičius', validators=[DataRequired()])
    submit = SubmitField("Užsakyti")

# Atsiliepimo forma
class FeedbackForm(FlaskForm):
    overall_assessment = IntegerField("Bendras vertinimas (1-10)", validators=[DataRequired(), NumberRange(min=0, max=10)])
    staff_assessment = IntegerField("Personalo įvertinimas (1-10)", validators=[DataRequired(), NumberRange(min=0, max=10)])
    comfort_assessment = IntegerField("Komforto vertinimas (1-10)", validators=[DataRequired(), NumberRange(min=0, max=10)])
    cleanliness_assessment = IntegerField("Švaros vertinimas (1-10)", validators=[DataRequired(), NumberRange(min=0, max=10)])
    place_assessment = IntegerField("Vietos vertinimas (1-10)", validators=[DataRequired(), NumberRange(min=0, max=10)])
    comment = StringField("Komentaras", validators=[DataRequired()])
    submit = SubmitField("Įrašyti")

class SearchApartments(FlaskForm):
    apartment_name = StringField("Apartamentų pavadinimas", render_kw={"placeholder": "Apartamentų pavadinimas"})
    submit = SubmitField("Ieškoti")

class SearchForUser(FlaskForm):
    user_name = StringField("Naudotojo pavardė", render_kw={"placeholder": "Naudotojo pavardė"})
    submit = SubmitField("Ieškoti")

class CreateApartment(FlaskForm):
    apartment_name = StringField("Apartamentų pavadinimas", validators=[DataRequired()])
    city = StringField("Miestas", validators=[DataRequired()])
    address = StringField("Adresas", validators=[DataRequired()])
    phone_number = StringField("Telefono numeris", validators=[DataRequired()])
    stars = IntegerField("Apartamentų žvaiždučių skaičius", validators=[DataRequired()])
    img_url = StringField("Nuotraukos nuoroda", validators=[DataRequired()])
    text = CKEditorField("Apartamentų aprašymas", validators=[DataRequired()])
    submit = SubmitField("Sukurti")