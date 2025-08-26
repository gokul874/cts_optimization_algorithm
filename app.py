from flask import Flask, render_template, redirect, url_for
from member.main import member_bp
from admin.routes import admin_bp

app = Flask(__name__)

# Register blueprints for member and admin functionalities
app.register_blueprint(member_bp, url_prefix='/member')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def home():
    return redirect(url_for('member.index'))
# Register route
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if Users.query.filter_by(username=username).first():
            return render_template("sign_up.html", error="Username already taken!")

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = Users(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))
    
    return render_template("sign_up.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Users.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")
if __name__ == '__main__':
    app.run(debug=True)
