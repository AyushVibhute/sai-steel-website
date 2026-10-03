# Sai Steel Furniture & Home Appliances — Business Website

A premium Flask + SQLite business website with:
- Product catalogue
- Product detail pages
- WhatsApp ordering
- Admin login
- Add / edit / delete products
- Product image upload
- Featured products
- Admin password change

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Install dependencies:

   pip install -r requirements.txt

4. Start:

   python app.py

5. Open:

   http://127.0.0.1:5000

## Admin

Open:
http://127.0.0.1:5000/admin/login

Initial login:
Username: admin
Password: admin123

IMPORTANT: Change the password immediately from the admin panel before publishing the site.

## WhatsApp

The site uses 9595216660 as the main WhatsApp ordering number. Change it in app.py if required.

## Production

Before deploying publicly:
- Set a strong SECRET_KEY environment variable.
- Change the admin password.
- Use HTTPS.
- Use a production WSGI server such as Gunicorn.
- Use a production database/storage strategy for uploaded images.
