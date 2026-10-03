import os
import sqlite3
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
UPLOAD_FOLDER.mkdir(exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            image TEXT,
            featured INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    admin = conn.execute("SELECT id FROM admin WHERE username = ?", ("admin",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123"))
        )

    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        seed = [
            ("Swami Samarth Frame", 300, "Gift & Frames",
             "Beautiful Swami Samarth devotional frame, suitable for home, office and gifting.",
             "swami-samarth-frame.png", 1),
            ("Pressure Cooker 5 Litre", 1250, "Kitchen Appliances",
             "5 litre pressure cooker for convenient everyday cooking.",
             "pressure-cooker.jpg", 1),
            ("Water Filter", 1400, "Home Appliances",
             "Practical water filter for everyday home use.",
             "water-filter.jpg", 1),
            ("Dinner Set", 600, "Kitchen & Dining",
             "Elegant dinner set for everyday dining and gifting.",
             "dinner-set.jpg", 1),
        ]
        conn.executemany("""
            INSERT INTO products (name, price, category, description, image, featured)
            VALUES (?, ?, ?, ?, ?, ?)
        """, seed)
    conn.commit()
    conn.close()

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_globals():
    return {
        "business_name": "Sai Steel Furniture & Home Appliances",
        "short_name": "Sai Steel",
        "location": "A/P-Chikurde, Near Warna Sinchan Main Road, Chikurde",
        "phone1": "9595216660",
        "phone2": "9860742578",
        "whatsapp": "919595216660",
    }

@app.route("/")
def home():
    conn = get_db()
    featured = conn.execute(
        "SELECT * FROM products WHERE featured = 1 ORDER BY id DESC LIMIT 8"
    ).fetchall()
    conn.close()
    return render_template("index.html", featured=featured)

@app.route("/products")
def products():
    category = request.args.get("category", "").strip()
    conn = get_db()
    categories = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()
    if category:
        rows = conn.execute(
            "SELECT * FROM products WHERE category = ? ORDER BY id DESC", (category,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("products.html", products=rows, categories=categories, selected_category=category)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    if not product:
        return render_template("404.html"), 404
    return render_template("product_detail.html", product=product)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ---------------- ADMIN ----------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        admin = conn.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    categories = conn.execute("SELECT COUNT(DISTINCT category) AS c FROM products").fetchone()["c"]
    featured = conn.execute("SELECT COUNT(*) AS c FROM products WHERE featured = 1").fetchone()["c"]
    recent = conn.execute("SELECT * FROM products ORDER BY id DESC LIMIT 5").fetchall()
    conn.close()
    return render_template("admin/dashboard.html", total=total, categories=categories, featured=featured, recent=recent)

@app.route("/admin/products")
@admin_required
def admin_products():
    conn = get_db()
    rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("admin/products.html", products=rows)

def save_uploaded_image(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return None
    filename = secure_filename(file.filename)
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    # Avoid collisions.
    filename = f"{stem}_{os.urandom(4).hex()}{suffix}"
    file.save(UPLOAD_FOLDER / filename)
    return filename

@app.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        featured = 1 if request.form.get("featured") else 0
        try:
            price = float(request.form.get("price", "0"))
        except ValueError:
            price = -1

        image = save_uploaded_image(request.files.get("image"))

        if not name or not category or price < 0:
            flash("Please enter a valid product name, category and price.", "error")
            return render_template("admin/add_product.html")

        conn = get_db()
        conn.execute("""
            INSERT INTO products (name, price, category, description, image, featured)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, price, category, description, image, featured))
        conn.commit()
        conn.close()
        flash("Product added successfully.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/add_product.html")

@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        conn.close()
        return render_template("404.html"), 404

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        featured = 1 if request.form.get("featured") else 0
        try:
            price = float(request.form.get("price", "0"))
        except ValueError:
            price = -1

        if not name or not category or price < 0:
            flash("Please enter a valid product name, category and price.", "error")
            conn.close()
            return render_template("admin/edit_product.html", product=product)

        new_image = save_uploaded_image(request.files.get("image"))
        image = new_image if new_image else product["image"]

        conn.execute("""
            UPDATE products
            SET name=?, price=?, category=?, description=?, image=?, featured=?
            WHERE id=?
        """, (name, price, category, description, image, featured, product_id))
        conn.commit()
        conn.close()
        flash("Product updated successfully.", "success")
        return redirect(url_for("admin_products"))

    conn.close()
    return render_template("admin/edit_product.html", product=product)

@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    conn.close()
    flash("Product deleted.", "success")
    return redirect(url_for("admin_products"))

@app.route("/admin/password", methods=["GET", "POST"])
@admin_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        conn = get_db()
        admin = conn.execute("SELECT * FROM admin WHERE username = ?", (session["admin_username"],)).fetchone()
        if not admin or not check_password_hash(admin["password_hash"], current):
            flash("Current password is incorrect.", "error")
        elif len(new) < 6:
            flash("New password must be at least 6 characters.", "error")
        elif new != confirm:
            flash("New passwords do not match.", "error")
        else:
            conn.execute(
                "UPDATE admin SET password_hash=? WHERE id=?",
                (generate_password_hash(new), admin["id"])
            )
            conn.commit()
            flash("Password changed successfully.", "success")
        conn.close()
    return render_template("admin/password.html")

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    init_db()
