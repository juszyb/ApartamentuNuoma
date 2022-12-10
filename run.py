from apartments import app
from apartments.sendmail import sendmail, RepeatTimer

##We are now creating a thread timer and controling it
timer = RepeatTimer(30,sendmail)
timer.start() #recalling run

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
