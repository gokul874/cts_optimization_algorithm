from flask import Flask, render_template, request, redirect, url_for
from member.data_processor import process_member_data
from admin.routes import admin_bp

app = Flask(__name__)

# Register the admin blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/member', methods=['GET', 'POST'])
def member():
    if request.method == 'POST':
        # Handle member data processing
        data = request.form['data']
        process_member_data(data)
        return redirect(url_for('index'))
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)