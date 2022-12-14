from flask import render_template, url_for, redirect, flash, request
from apartments import app, db, mail
from apartments.forms import UserRegistrationForm, BookingForm, UpdateProfileForm, UserLoginForm, \
    VendorRegistrationForm, FeedbackForm, SearchApartments, SearchForUser, CreateApartment, AddRoom
from apartments.models import User, PropertyOwner, Apartment, Tenant, Room, RoomType, Feedback, room_reservation, \
    BookingStatus, Booking, Bill, Payment, admin_only, owner_only
from flask_login import login_user, current_user, logout_user, login_required
from flask_googlemaps import get_coordinates
import folium
from datetime import datetime
from werkzeug.exceptions import NotFound
import stripe
import stripe.error
import requests
import os
from flask_mail import Message

@app.route("/", methods=["GET", "POST"])
def main_page():
    form = SearchApartments()
    apartments_list = Apartment.query.all()
    if form.validate_on_submit():
        aps = form.apartment_name.data
        search = "%{}%".format(aps)
        apartments_list = Apartment.query.filter(Apartment.apartment_name.like(search)).all()
    return render_template('index.html', form=form, apartments_list=apartments_list)


@app.route("/apartment/<int:apartment_id>", methods=["GET", "POST"])
def show_apartment(apartment_id):
    requested_apartment = Apartment.query.get(apartment_id)
    # Iš lentelių Room ir RoomType išrenka visus įrašus pagal kambario tipą, pagal apartamentus, pagal kambario laisvumą
    room_list = db.session.query(Room, RoomType).filter(Room.fk_room_type_id == RoomType.id).filter(
        Room.fk_apartment_id == requested_apartment.id). \
        filter(Room.free_room == 1).all()

    feedbacks = db.session.query(Feedback, Tenant, User).filter(
        Feedback.fk_apartment_id == apartment_id
    ).filter(
        Feedback.fk_tenant_id == Tenant.id
    ).filter(
        Tenant.fk_user_id == User.id
    ).all()

    OWM_ENDPOINT = "https://api.openweathermap.org/data/2.5/forecast/daily"
    weather_parameters = {
        "lat": requested_apartment.latitude,
        "lon": requested_apartment.longitude,
        "cnt": "5",
        "units": "metric",
        "appid": "69f04e4613056b159c2761a9d9e664d2"
    }

    response = requests.get(OWM_ENDPOINT, params=weather_parameters)
    response.raise_for_status()

    weather_data = response.json()
    # weather_slice = weather_data["hourly"][:12]
    test = weather_data['list']

    weather = {0: [], 1: [], 2: [], 3: [], 4: []}

    keys = range(5)
    for i in keys:
        t = test[i]['temp']['day']
        w = test[i]['weather'][0]['main']
        weather[i].append(t)
        weather[i].append(w)

    # result = Room.query.filter(Room.fk_apartment_id == requested_apartment.id).filter(Room.free_room == 1).all()
    return render_template('apartment.html', apartment=requested_apartment, rooms=room_list, feedbacks_list=feedbacks, weather=weather)


@app.route("/map/<int:apartment_id>")
def show_map(apartment_id):
    requested_apartment = Apartment.query.get(apartment_id)
    map = folium.Map(
        location=[requested_apartment.latitude, requested_apartment.longitude],
        zoom_start=12
    )
    folium.Marker(
        location=[requested_apartment.latitude, requested_apartment.longitude],
        popup="<i>Marker here</i>",
        tooltip="Click here"
    ).add_to(map)

    return map._repr_html_()


@app.route("/room-reservation/<int:room_id>", methods=["GET", "POST"])
@login_required
def book_room(room_id):
    # Suranda kambarį pagal kambario id
    room = Room.query.get(room_id)
    # Suranda apartamentus pagal kambario id
    apartment = Apartment.query.filter(Apartment.id == room.fk_apartment_id).first()
    #Randa kambario tipą pagal room id
    room_type = RoomType.query.get(room.fk_room_type_id)
    # Išspausdina formą
    form = BookingForm()
    if form.validate_on_submit():

        # Tikrina, ar teisingas laikas
        if form.arrival_date.data >= form.departure_date.data:
            flash("Pasirinkote klaidingas dienas", "danger")
            return redirect(url_for('show_apartment', apartment_id=apartment.id))

        # Tikrina, ar nuomininkas jau egzistuoja. Jei neegzistuoja, sukuria naują
        try:
            tenant = Tenant.query.filter(Tenant.fk_user_id == current_user.id).first_or_404()
        except NotFound:
            tenant = Tenant(fk_user_id=current_user.id)
            db.session.add(tenant)
            db.session.flush()

        # convert string to date object
        d1 = datetime.strptime(str(form.departure_date.data), "%Y-%m-%d")
        d2 = datetime.strptime(str(form.arrival_date.data), "%Y-%m-%d")

        # difference between dates in timedelta
        delta = d1 - d2
        number_of_nights = int(delta.days)

        new_bill = Bill(
            full_price=number_of_nights*(float(room_type.price_for_night) + float(room.room_fees) + float(room.breakfast_fees) + float(room.other_fees)),
            date=datetime.now(),
            fk_tenant_id=tenant.id
        )
        db.session.add(new_bill)
        db.session.flush()
        # Pagal userio formą užpildomas naujas užsakymas
        new_booking = Booking(
            arrival_date=form.arrival_date.data,
            departure_date=form.departure_date.data,
            num_of_persons=form.people_nr.data,
            status=BookingStatus.ongoing,
            fk_tenant_id=tenant.id,
            fk_bill_id=new_bill.id
        )
        new_payment = Payment(
            completed=False,
            date=datetime.now(),
            fk_bill_id=new_bill.id
        )

        #Kadangi po užsakymo kambarys tampa nebelaisvas, tai pasikeičia kambario būsena
        # room.free_room = False

        db.session.add(new_booking)
        db.session.add(new_payment)
        db.session.flush()
        # Užpildoma kambario rezervacijos lentelė
        new_room_reservation = room_reservation.insert().values(room_id=room_id, booking_id=new_booking.id)
        db.session.execute(new_room_reservation)
        db.session.commit()
        flash("Jūsų užsakymas sėkmingai pridėtas į krepšelį", "success")
        return redirect(url_for('main_page'))
    return render_template("booking-form.html", form=form, room=room)

@app.route('/booking-list', methods=["GET", "POST"])
@login_required
def view_bookings_list():
    try:
        tenant = Tenant.query.filter(Tenant.fk_user_id == current_user.id).first_or_404()
    except NotFound:
        flash("Jūsų užsakymų nėra", "danger")
        return redirect(url_for('main_page'))

    ongoing_bookings = db.session.query(Bill, Booking, room_reservation, Room, Apartment).filter(
        Booking.fk_tenant_id == tenant.id
    ).filter(
        Bill.fk_tenant_id == tenant.id
    ).filter(
        Booking.fk_bill_id == Bill.id
    ).filter(
        Booking.status == BookingStatus.ongoing
    ).filter(
        Booking.id == room_reservation.c.booking_id
    ).filter(
        Room.id == room_reservation.c.room_id
    ).filter(
        Apartment.id == Room.fk_apartment_id
    ).all()

    return render_template("bookings.html", bookings=ongoing_bookings)

@app.route('/booking-list/<int:booking_id>/delete', methods=["GET", "POST"])
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    booking.status = BookingStatus.cancelled
    db.session.commit()
    flash("Jūsų užsakymas sėkmingai atšauktas", "success")
    return redirect(url_for('main_page'))


@app.route("/booking-list/booking/<int:booking_id>", methods=["GET", "POST"])
@login_required
def confirm_payment(booking_id):

    tenant = Tenant.query.filter(Tenant.fk_user_id == current_user.id).first_or_404()

    booking = db.session.query(Booking, room_reservation, Room, Apartment, Bill, RoomType, Payment).filter(
        Booking.fk_tenant_id == tenant.id
    ).filter(
        Booking.id == booking_id
    ).filter(
        Booking.status == BookingStatus.ongoing
    ).filter(
        Booking.id == room_reservation.c.booking_id
    ).filter(
        Room.id == room_reservation.c.room_id
    ).filter(
        Apartment.id == Room.fk_apartment_id
    ).filter(
        Bill.id == Booking.fk_bill_id
    ).filter(
        RoomType.id == Room.fk_room_type_id
    ).filter(
        Payment.fk_bill_id == Bill.id
    ).all()[0]

    print(booking)

    if booking.Payment.completed:
        flash("Jūs jau apmokėjote šį užsakymą", "danger")
        return redirect(url_for('view_bookings_list'))

    # Sukuriamas apmokėjimas stripe platformoje
    try:
        stripe.Product.retrieve(f"{booking.Bill.id}")
    except stripe.error.InvalidRequestError:
        bill = stripe.Product.create(
            id=booking.Bill.id,
            name=booking.RoomType.type_name,
            default_price_data={
                "unit_amount_decimal": round(booking.Bill.full_price * 100, 2),
                "currency": 'EUR'
            }
        )

    return render_template("confirm-booking.html", booking=booking)

@app.route('/create-checkout-session/<int:bill_id>', methods=["GET", "POST"])
def create_checkout_session(bill_id):
    # Sąskaita yra kaip produktas,
    bill = stripe.Product.retrieve(f"{bill_id}")
    try:
        session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': bill['default_price'],
                    'quantity': 1
                }
            ],
            mode='payment',
            success_url="http://127.0.0.1:5000" + "/success?session_id={CHECKOUT_SESSION_ID}" + f"&product_id={bill_id}",
            cancel_url="http://127.0.0.1:5000" + "/cancel"
        )
    except Exception as e:
        return str(e)

    return redirect(session.url, code=303)

@app.route('/success')
def success_message():
    #Grąžina apmokėjimo informaciją, jame galima rast payment status, kuris parodo, ar jau įvykdytas apmokėjimas
    session = stripe.checkout.Session.retrieve(request.args.get('session_id'))
    #Grąžina sąskaitą su jos nr, pagal ką galiu patvirtinti, kuri sąskaita priklauso kuriam apmokėjimui
    product = stripe.Product.retrieve(request.args.get('product_id'))

    #Pakeičiama apmokėjimo busena į užbaigtą
    payment = Payment.query.filter(Payment.fk_bill_id == product['id']).first()
    payment.completed = True

    #Pakeičiama užsakymo būsena į užbaigtą
    booking = Booking.query.filter(Booking.fk_bill_id == product['id']).first()
    booking.status = BookingStatus.finished

    db.session.commit()

    return render_template('success.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_page'))
    form = UserRegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            last_name=form.name.data,
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            birth_date=form.birth_date.data,
            phone_number=form.phone_number.data
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("main_page"))
    return render_template("register.html", form=form)


@app.route("/register-for-owner", methods=["GET", "POST"])
def register_for_owner():
    if current_user.is_authenticated:
        return redirect(url_for('main_page'))
    form = VendorRegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            last_name=form.name.data,
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
            birth_date=form.birth_date.data,
            phone_number=form.phone_number.data
        )
        new_company = PropertyOwner(
            company_name=form.company_name.data,
            company_code=form.company_name.data
        )
        new_user.property_owner.append(new_company)
        db.session.add(new_user)
        db.session.add(new_company)
        db.session.commit()

        return redirect(url_for("main_page"))
    return render_template("register-for-owner.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_page'))
    form = UserLoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main_page'))
        else:
            flash('Prisijungimas nesėkmingas. Bandykite dar kartą.', 'danger')

    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main_page'))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile_page():


    form = UpdateProfileForm(
        name=current_user.name,
        last_name=current_user.last_name,
        username=current_user.username,
        email=current_user.email,
        birth_date=current_user.birth_date,
        phone_number=current_user.phone_number
    )
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.last_name = form.last_name.data
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.phone_number = form.phone_number.data
        db.session.commit()
        flash('Jūsų duomenys sėkmingai atnaujinti!', 'success')
        return redirect(url_for('profile_page'))
    return render_template("profile.html", form=form)


@app.route("/booking-history")
@login_required
def history_page():
    try:
        user = Tenant.query.filter(Tenant.fk_user_id == current_user.id).first_or_404()
    except NotFound:
        flash("Jūs neturite užsakymų istorijos", "danger")
        return redirect(url_for('profile_page'))


    finished_bookings = db.session.query(Bill, Booking, room_reservation, Room, Apartment).filter(
        Booking.fk_tenant_id == user.id
    ).filter(
        Booking.fk_tenant_id == user.id
    ).filter(
        Bill.fk_tenant_id == user.id
    ).filter(
        Booking.fk_bill_id == Bill.id
    ).filter(
        Booking.status == BookingStatus.finished
    ).filter(
        Booking.id == room_reservation.c.booking_id
    ).filter(
        Room.id == room_reservation.c.room_id
    ).filter(
        Apartment.id == Room.fk_apartment_id
    ).all()

    return render_template("booking-history.html", history=finished_bookings)


@app.route("/feedback-create/<int:booking_id>", methods=["GET", "POST"])
@login_required
def create_feedback(booking_id):
    # Grąžina užsakymą pagal užsakymo numerį
    requested_booking = Booking.query.get(booking_id)
    if Feedback.query.filter(Feedback.fk_booking_id == requested_booking.id).first():
        flash("Atsiliepimas jau sukurta, jį galite tik redaguoti", "danger")
        return redirect(url_for("history_page"))
    # Iš lentelės room_reservation ištraukia visus duomenis pagal norimo užsakymo id
    room_type = db.session.query(room_reservation).where(room_reservation.c.booking_id == requested_booking.id).first()
    # Iš Room lentelės paima kambario duomenis pagal kambario tipo id
    room = Room.query.get(room_type.room_id)
    # Randa nuomininko id pagal current userį
    tenant = db.session.query(Tenant).where(Tenant.fk_user_id == current_user.id).first()
    # Randa hotelių duomenis pagal room type id
    apartment = Apartment.query.get(room.fk_apartment_id)
    form = FeedbackForm()

    if form.validate_on_submit():
        new_feedback = Feedback(
            overall_assessment=form.overall_assessment.data,
            staff_assessment=form.staff_assessment.data,
            comfort_assessment=form.comfort_assessment.data,
            cleanliness_assessment=form.cleanliness_assessment.data,
            place_assessment=form.place_assessment.data,
            comment=form.comment.data,
            date=datetime.now(),
            fk_booking_id=requested_booking.id,
            fk_tenant_id=tenant.id,
            fk_apartment_id=apartment.id
        )
        db.session.add(new_feedback)
        db.session.commit()
        flash("Atsiliepimas sėkmingai sukurtas", "success")
        return redirect(url_for("history_page"))
    return render_template("feedback-form.html", booking=requested_booking, form=form)


@app.route("/feedback-edit/<int:booking_id>", methods=["GET", "POST"])
@login_required
def edit_feedback(booking_id):
    requested_booking = Booking.query.get(booking_id)
    requested_feedback = Feedback.query.filter(Feedback.fk_booking_id == requested_booking.id).first()
    if not requested_feedback:
        flash("Atsiliepimas dar nėra sukurta, jį galite tik sukurti", "danger")
        return redirect(url_for("history_page"))

    # result = Booking.query.join(room_reservation).join(Room).join(Apartment).join(Feedback).all()
    edit_form = FeedbackForm(
        overall_assessment=requested_feedback.overall_assessment,
        staff_assessment=requested_feedback.staff_assessment,
        comfort_assessment=requested_feedback.comfort_assessment,
        cleanliness_assessment=requested_feedback.cleanliness_assessment,
        place_assessment=requested_feedback.place_assessment,
        comment=requested_feedback.comment,
        date=requested_feedback.date
    )

    if edit_form.validate_on_submit():
        requested_feedback.overall_assessment = edit_form.overall_assessment.data
        requested_feedback.staff_assessment = edit_form.staff_assessment.data
        requested_feedback.comfort_assessment = edit_form.comfort_assessment.data
        requested_feedback.cleanliness_assessment = edit_form.cleanliness_assessment.data
        requested_feedback.place_assessment = edit_form.place_assessment.data
        requested_feedback.comment = edit_form.comment.data
        requested_feedback.date = datetime.now()
        db.session.commit()

        flash("Atsiliepimas sėkmingai paredaguotas", "success")
        return redirect(url_for("history_page"))
    return render_template("feedback-form.html", booking=requested_booking, form=edit_form, is_edit=True)
@app.route("/admin-feedback-list/<int:booking_id>/delete", methods=["GET", "POST"])
@login_required
@admin_only
def delete_feedback(booking_id):
    requested_feedback = Feedback.query.filter(Feedback.fk_booking_id == booking_id).first()
    db.session.delete(requested_feedback)
    db.session.commit()
    flash("Naudotojo atsiliepimas sėkmingai pašalintas", "success")
    return redirect(url_for('admin_page'))

@app.route("/admin-list", methods=["GET", "POST"])
@login_required
@admin_only
def admin_page():
    user_list = User.query.all()
    form = SearchForUser()
    if form.validate_on_submit():
        user = form.user_name.data
        search = "%{}%".format(user)
        user_list = User.query.filter(User.last_name.like(search)).all()
    return render_template("admin-list.html", form=form, user_list=user_list)

@app.route("/admin-list/<int:user_id>/delete", methods=["GET", "POST"])
@login_required
@admin_only
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    print(user_id)
    print(user.id)
    if Tenant.query.filter(Tenant.fk_user_id == user_id).first():

        flash("Naudotojo pašalinti negalima, nes ji yra nuomininkas", "danger")
        return redirect(url_for('main_page'))
    elif PropertyOwner.query.filter(PropertyOwner.fk_user_id == user_id).first():
        flash("Naudotojo pašalinti negalima, nes ji yra nuomotojas", "danger")
        return redirect(url_for('main_page'))
    else:
        db.session.delete(user)
        db.session.commit()
        flash("Naudotojo sėkmingai pašalintas", "success")
        return redirect(url_for('main_page'))


@app.route("/admin-feedback-list/<int:user_id>", methods=["GET", "POST"])
@login_required
@admin_only
def show_feedback_list(user_id):
    # user = Tenant.query.filter(Tenant.fk_user_id == user_id).first()
    # print(user.id)
    # result = db.session.query(Feedback, Apartment).filter(Feedback.fk_apartment_id == Apartment.id).all()
    try:
        Tenant.query.filter(Tenant.fk_user_id == user_id).first_or_404()
    except NotFound:
        flash("Naudotojas nėra parašęs atsiliepimų", "danger")
        return redirect(url_for('admin_page'))

    user = Tenant.query.filter(Tenant.fk_user_id == user_id).first_or_404()
    if Feedback.query.filter(Feedback.fk_tenant_id == user.id):
        results = db.session.query(Feedback, Apartment).filter(
            Feedback.fk_tenant_id == user.id
        ).filter(
            Feedback.fk_apartment_id == Apartment.id
        ).all()
    else:
        flash("Naudotojas nėra parašęs atsiliepimų", "danger")
        return redirect(url_for('admin_page'))

    return render_template("admin-feedback-list.html", feedbacks=results)

@app.route("/property-owner-list", methods=["GET", "POST"])
@login_required
def property_owner_apartments():
    try:
        PropertyOwner.query.filter(PropertyOwner.fk_user_id == current_user.id).first_or_404()
    except NotFound:
        flash("Jūs nesate nuomotojos, todėl peržiūrėti negalite", "danger")
        return redirect(url_for('main_page'))

    #Suranda nuomotoją pagal current userį
    property_owner = PropertyOwner.query.filter(PropertyOwner.fk_user_id == current_user.id).first_or_404()
    #Suranda apartamentus pagal nuomotojo id
    result = Apartment.query.filter(Apartment.fk_property_owner_id == property_owner.id)

    return render_template("property-owner-list.html", apartments_list=result)

@app.route('/property-owner-list/create', methods=["GET", "POST"])
@login_required
@owner_only
def create_apartment():
    form = CreateApartment()

    if form.validate_on_submit():
        city = form.city.data
        address = form.address.data
        full_address = f"{address}, {city}"
        API = os.environ.get("GOOGLEMAPS_API_KEY")
        cord = get_coordinates(API_KEY=API, address_text=full_address)
        new_apartment = Apartment(
            apartment_name=form.apartment_name.data,
            city=form.city.data,
            address=form.address.data,
            phone_number=form.phone_number.data,
            stars=form.stars.data,
            img_url=form.img_url.data,
            latitude=cord['lat'],
            longitude=cord['lng'],
            text=form.text.data,
            fk_property_owner_id=current_user.id
        )
        db.session.add(new_apartment)
        db.session.commit()
        flash("Apartamentų skelbimas sėkmingai sukurtas", "success")
        return redirect(url_for("property_owner_apartments"))
    return render_template("add-apartment.html", form=form)

@app.route('/property-owner-list/edit/<int:apartment_id>', methods=["GET", "POST"])
@login_required
@owner_only
def edit_apartment(apartment_id):
    requested_apartment = Apartment.query.get(apartment_id)
    edit_form = CreateApartment(
        apartment_name=requested_apartment.apartment_name,
        city=requested_apartment.city,
        address=requested_apartment.address,
        phone_number=requested_apartment.phone_number,
        stars=requested_apartment.stars,
        img_url=requested_apartment.img_url,
        text=requested_apartment.text
    )
    if edit_form.validate_on_submit():
        requested_apartment.apartment_name = edit_form.apartment_name.data
        requested_apartment.city = edit_form.city.data
        requested_apartment.address = edit_form.address.data
        requested_apartment.phone_number = edit_form.phone_number.data
        requested_apartment.stars = edit_form.stars.data
        requested_apartment.img_url = edit_form.img_url.data
        requested_apartment.text = edit_form.text.data
        db.session.commit()

        flash("Apartamentų skelbimas sėkmingai paredaguotas", "success")
        return redirect(url_for("property_owner_apartments"))
    return render_template("add-apartment.html", form=edit_form, exits=True)

@app.route('/property-owner-list/<int:apartment_id>/delete', methods=["GET", "POST"])
@login_required
@owner_only
def delete_apartment(apartment_id):
    apartment = Apartment.query.get_or_404(apartment_id)

    #Tikrinama, ar apartamentų kambariai buvo įtraukti į rezervaciją
    is_booked = db.session.query(Apartment, Room, room_reservation).filter(apartment.id == Room.fk_apartment_id).filter(
        room_reservation.c.room_id == Room.id
    ).all()

    if is_booked:
        flash("Apartamento pašalinti negalima, nes jis yra/buvo rezervuotas", "danger")
        return redirect(url_for("property_owner_apartments"))
    else:
        if Room.query.filter(Room.fk_apartment_id == apartment.id).all():
            room = Room.query.filter(Room.fk_apartment_id == apartment.id).all()
            db.session.delete(room)

        db.session.delete(apartment)
        db.session.commit()
        flash("Apartmentų skelbimas sėkmingai pašalintas", "success")
        return redirect(url_for("property_owner_apartments"))

@app.route('/property-owner-list/add-room/<int:apartment_id>', methods=["GET", "POST"])
@login_required
@owner_only
def add_room(apartment_id):
    form = AddRoom()
    if form.validate_on_submit():
        new_room_type = RoomType(
            type_name=form.type_name.data,
            price_for_night=form.price_for_night.data,
            number_of_beds=form.number_of_beds.data
        )
        db.session.add(new_room_type)
        db.session.flush()
        new_room = Room(
            text=form.text.data,
            room_number=form.room_number.data,
            room_fees=form.room_fees.data,
            breakfast_fees=form.breakfast_fees.data,
            other_fees=form.other_fees.data,
            fk_apartment_id=apartment_id,
            fk_room_type_id=new_room_type.id
        )
        db.session.add(new_room)
        db.session.commit()
        flash("Sėkmingai pridėjote naują kambarį", "success")
        return redirect(url_for('property_owner_apartments'))

    return render_template("add-room.html", form=form)
