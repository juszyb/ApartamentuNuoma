import time
from datetime import datetime, timedelta
from threading import Timer
import smtplib, ssl
from apartments import app, db
from apartments.models import Booking, Payment, Tenant, User


def sendmail():
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls
    sender_email = ""
    password = ""

    # Create a secure SSL context
    context = ssl.create_default_context()
    #print(datetime.now().date() + timedelta(days=1))


    date1 =datetime.now().date() + timedelta(days=1)
    date2 = datetime.now().date() + timedelta(days=2)
    with app.app_context():
        results = db.session.query(Booking, Payment, Tenant, User).filter(
            Booking.arrival_date >= date1
        ).filter(
            Booking.arrival_date < date2
        ).filter(
            Booking.fk_tenant_id == Tenant.id
        ).filter(
            Tenant.fk_user_id == User.id
        ).filter(
            Payment.fk_bill_id == Booking.fk_bill_id
        ).filter(
            Payment.completed == 1
        ).filter(
            Booking.send_mail == 0
        ).all()

        for result in results:
            #print(result.Booking.arrival_date.strftime("%m/%d/%Y") + ' ' + str(result.Booking.id))
            try:
                with smtplib.SMTP(smtp_server, port) as server:
                    server.ehlo()  # Can be omitted
                    server.starttls(context=context)
                    server.ehlo()  # Can be omitted
                    server.login(sender_email, password)
                    server.sendmail(sender_email, result.User.email, "test" + result.Booking.arrival_date.strftime("%m/%d/%Y") + ' ' + str(result.Booking.id))
                    result.Booking.send_mail = 1
                    db.session.commit()
            except Exception as e:
                # Print any error messages to stdout
                print(e)


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args,**self.kwargs)
            #print(' ')

