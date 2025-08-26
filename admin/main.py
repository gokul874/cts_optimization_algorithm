from flask import Flask
from admin.routes import admin_bp
from member.main import member_bp

app = Flask(__name__)

# Register blueprints for admin and member functionalities
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(member_bp, url_prefix='/member')

if __name__ == '__main__':
    app.run(debug=True)