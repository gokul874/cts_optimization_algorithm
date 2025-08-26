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

if __name__ == '__main__':
    app.run(debug=True)