from sifec_base import LocalGateway, base_logger, PeriodicTrigger, ExampleEventFabric
from utils import *
from datetime import datetime
import smtplib
from email.message import EmailMessage
from config import *

app = LocalGateway(mock=False)

def send_email(to, subj, body):
    msg = EmailMessage()
    msg["from"] = "German Authority Against Emotional Violence and Manipulation", 
    msg["Subject"] = subj
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(MAIL_USR, MAIL_PASS)
        smtp.send_message(msg)

def handle_emergency(data:dict):
    print(f"emergency event received!")
    data = data.get("emergency_event").get("data")
    print(data)
    todo = Todo(
        text=data.get("task"),
        timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else None,
        priority=data.get("priority")
    )
    todo.push_to_influx()

    if data.get("priority") < 2:
        send_email(to=MAIL_DEST, subj="Emergency Alert", body=f"""
            An emergency occured at {data.get("timestamp")}. 
            
            Location: {data.get("location")}

            {data.get("text")}
        """)

    return

app.deploy(cb=handle_emergency, name="handle_emergency", evts="emergency_event", method="POST")

