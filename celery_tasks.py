import os
import smtplib
from datetime import datetime
from email import encoders
from email.message import EmailMessage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from celery import Celery

from db import db
from pdf import PDFReport

celery = Celery('tasks', broker=os.environ.get('CELERY_BROKER_URL'))

cart_collection = db['cart']


@celery.task
def send_order_email(order_id: str, email_to: str):
    email = EmailMessage()
    email['Subject'] = 'Your order info'
    email['From'] = os.environ.get("GMAIL_USER")
    email['To'] = email_to

    email.set_content(f'You have successfully placed an order. Your order ID is {order_id}.')
    with smtplib.SMTP_SSL(os.environ.get('SMTP_HOST'), int(os.environ.get('SMTP_PORT'))) as server:
        server.ehlo()
        server.login(os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_PASS"))
        server.send_message(email)


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(3600.0, delete_expired_carts.s(), name='delete expired carts')


@celery.task
def delete_expired_carts():
    expiration_time = datetime.utcnow()
    cart_collection.delete_many({'expiration_time': {'$lt': expiration_time}})


@celery.task
def send_bill_email(order):
    body = 'Please, find attached the invoice for your recent purchase.'

    message = MIMEMultipart()
    message['From'] = os.environ.get("GMAIL_USER")
    message['To'] = order['email']
    message['Subject'] = f'Invoice for order {order["_id"]}'
    message.attach(MIMEText(body, 'plain'))

    pdf_name = 'invoice.pdf'
    report = PDFReport()
    report_binary = report.get_report(order)
    payload = MIMEBase('application', 'octate-stream', Name=pdf_name)
    payload.set_payload(report_binary)
    encoders.encode_base64(payload)

    payload.add_header('Content-Decomposition', 'attachment', filename='invoice.pdf')
    message.attach(payload)

    with smtplib.SMTP_SSL(os.environ.get('SMTP_HOST'), int(os.environ.get('SMTP_PORT'))) as server:
        server.ehlo()
        server.login(os.environ.get("GMAIL_USER"), os.environ.get("GMAIL_PASS"))
        server.send_message(message)
