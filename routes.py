import os
import pandas as pd
import json
from flask import render_template, request, jsonify, redirect, url_for, flash, session, send_file
from werkzeug.utils import secure_filename
from app import app, db
from models import Dataset, OptimizationResult, MemberProviderAssignment
from utils.data_processor import DataProcessor
from utils.optimizer import NetworkOptimizer
from utils.geospatial import GeospatialAnalyzer
import logging
from functools import wraps

import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from data_processor import DataProcess

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'csv'}

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Demo member credentials (in production, this would come from a database)
DEMO_MEMBER_CREDENTIALS = {
    "M001": "member123",
    "M002": "member456", 
    "M003": "member789"
}

# Member portal URL (your member-side application is now integrated)
MEMBER_PORTAL_URL = "/member"

data_process = DataProcess()

# -----------------------------
# SMTP / Email Config
# -----------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465  # SSL
SMTP_USER = "netsenseservices@gmail.com"           # Your Gmail
SMTP_PASS = "ukhr zqxo gihn yyak"              # Gmail App Password
ADMIN_EMAIL = "netsenseservices@gmail.com"         # Admin fallback


def send_email(to_email: str, subject: str, body: str, reply_to: str | None = None, bcc: str | None = None):
    """Send email via Gmail SMTP with SSL."""
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to

    recipients = [to_email]
    if bcc and bcc not in recipients:
        recipients.append(bcc)

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, recipients, msg.as_string())

@app.route('/search_providers', methods=['POST'])
def search_providers():
    try:
        user_lat = float(request.form.get('latitude'))
        user_lon = float(request.form.get('longitude'))
        provider_type = (request.form.get('provider_type') or 'Hospital').lower()

        providers = data_process.find_nearby_providers(
            user_lat, user_lon, provider_type, radius_km=15
        )

        sorted_providers = data_process.sort_providers_by_priority(providers)

        return jsonify({
            'success': True,
            'providers': sorted_providers,
            'count': len(sorted_providers)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/get_provider_types')
def get_provider_types():
    types = data_process.get_provider_types()
    return jsonify({'success': True, 'types': types})


# -----------------------------
# Feedback: send to provider or admin
# -----------------------------
@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    try:
        # ✅ Parse JSON instead of form
        data = request.get_json(silent=True) or {}
        provider_email = (data.get('provider') or "").strip()
        message = (data.get('feedback') or "").strip()
        member_name = (data.get('member_name') or "Anonymous").strip()
        member_email = (data.get('member_email') or "").strip()

        if not message:
            return jsonify({'success': False, 'error': 'Message is required.'}), 400

        # Always fallback to admin if provider email missing
        if not provider_email:
            provider_email = ADMIN_EMAIL

        # Compose email body
        body_lines = [
            f"New feedback from: {member_name}",
        ]
        if member_email:
            body_lines.append(f"Member email: {member_email}")
        body_lines.append("")
        body_lines.append("Message:")
        body_lines.append(message)
        body = "\n".join(body_lines)

        subject = f"Healthcare Finder: Feedback from {member_name}"

        # Send email
        send_email(
            to_email=provider_email,
            subject=subject,
            body=body,
            reply_to=member_email if member_email else None,
            bcc=ADMIN_EMAIL if provider_email != ADMIN_EMAIL else None
        )

        return jsonify({'success': True, 'message': 'Feedback sent successfully!'})
    except Exception as e:
        print(f"❌ Error sending feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please login to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('user_type') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_type = request.form.get('login_type', 'admin')
        
        if login_type == 'admin':
            username = request.form['username']
            password = request.form['password']
            
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                session['logged_in'] = True
                session['username'] = username
                session['user_type'] = 'admin'
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_index'))
            else:
                flash('Invalid admin credentials', 'error')
        
        elif login_type == 'member':
            member_id = request.form['member_id']
            password = request.form['password']
            
            # Check demo credentials (in production, check against database)
            if member_id in DEMO_MEMBER_CREDENTIALS and DEMO_MEMBER_CREDENTIALS[member_id] == password:
                session['logged_in'] = True
                session['member_id'] = member_id
                session['user_type'] = 'member'
                flash('Member login successful! Welcome to your healthcare portal.', 'success')
                # Redirect to integrated member portal
                return redirect(url_for('member_interface'))
            else:
                flash('Invalid member credentials', 'error')
    
    return render_template('login.html')

@app.route('/admin')
@admin_required
def admin_index():
    return render_template('admin_index.html')

@app.route('/member_portal')
def member_portal_redirect():
    """Redirect to integrated member portal"""
    if session.get('user_type') == 'member':
        return redirect(url_for('member_interface'))
    else:
        flash('Please login as a member first', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    user_type = session.get('user_type', 'admin')
    session.clear()
    flash(f'{user_type.title()} logout successful', 'success')
    return redirect(url_for('login'))

# Main application routes (admin only)
@app.route('/')
def index():
    # Check if user is logged in, if not redirect to login
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # If member is logged in, redirect to member portal
    if session.get('user_type') == 'member':
        return redirect(url_for('member_interface'))
    
    # Admin users go to admin dashboard
    return redirect(url_for('admin_index'))

@app.route('/member_interface')
def member_interface():
    """Member healthcare provider finder interface"""
    # Check if user is logged in as member
    if not session.get('logged_in') or session.get('user_type') != 'member':
        flash('Please login as a member to access the member portal', 'error')
        return redirect(url_for('login'))
    
    return render_template('member_interface.html')

@app.route('/upload')
@admin_required
def upload_page():
    datasets = Dataset.query.order_by(Dataset.upload_date.desc()).all()
    return render_template('upload.html', datasets=datasets)

@app.route('/upload_dataset', methods=['POST'])
@admin_required
def upload_dataset():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file selected'}), 400
        
        file = request.files['file']
        dataset_type = request.form.get('dataset_type')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload a CSV file.'}), 400
        
        if dataset_type not in ['members', 'providers']:
            return jsonify({'error': 'Invalid dataset type'}), 400
        
        # Secure filename and save
        filename = secure_filename(file.filename)
        timestamp = str(int(pd.Timestamp.now().timestamp()))
        filename = f"{dataset_type}_{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process and validate the dataset
        processor = DataProcessor()
        
        if dataset_type == 'members':
            df, errors = processor.process_members_data(filepath)
        else:
            df, errors = processor.process_providers_data(filepath)
        
        if errors:
            # Remove the uploaded file if there were errors
            os.remove(filepath)
            return jsonify({'error': f'Data validation errors: {"; ".join(errors)}'}), 400
        
        # Save dataset info to database
        dataset = Dataset(
            name=file.filename,
            file_type=dataset_type,
            filename=filename,
            record_count=len(df),
            is_processed=True
        )
        db.session.add(dataset)
        db.session.commit()
        
        logger.info(f"Successfully uploaded {dataset_type} dataset with {len(df)} records")
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {dataset_type} dataset with {len(df)} records',
            'dataset_id': dataset.id,
            'record_count': len(df)
        })
        
    except Exception as e:
        logger.error(f"Error uploading dataset: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/optimize_network', methods=['POST'])
@admin_required
def optimize_network():
    try:
        # Get the latest datasets
        members_dataset = Dataset.query.filter_by(file_type='members', is_processed=True).order_by(Dataset.upload_date.desc()).first()
        providers_dataset = Dataset.query.filter_by(file_type='providers', is_processed=True).order_by(Dataset.upload_date.desc()).first()
        
        if not members_dataset or not providers_dataset:
            return jsonify({'error': 'Both member and provider datasets are required'}), 400
        
        # Load data
        processor = DataProcessor()
        members_path = os.path.join(app.config['UPLOAD_FOLDER'], members_dataset.filename)
        providers_path = os.path.join(app.config['UPLOAD_FOLDER'], providers_dataset.filename)
        
        members_df, _ = processor.process_members_data(members_path)
        providers_df, _ = processor.process_providers_data(providers_path)
        
        # Initialize optimizer
        optimizer = NetworkOptimizer()
        geospatial = GeospatialAnalyzer()
        
        # Use optimized algorithm for large datasets
        logger.info("Finding candidate provider connections using optimized algorithm...")
        
        # Sample data for demonstration with large datasets
        members_sample = members_df
        providers_sample = providers_df
        
        candidate_connections = optimizer.find_candidate_connections(
            members_sample, providers_sample, geospatial, max_distance=15.0
        )
        
        logger.info(f"Found {len(candidate_connections)} candidate connections")
        
        # Optimize assignments
        assignments = optimizer.optimize_assignments(candidate_connections, members_sample, providers_sample)
        
        # Calculate metrics
        total_members = len(members_sample)
        served_members = len([a for a in assignments if a['provider_id'] is not None])
        unserved_members = total_members - served_members
        access_percentage = (served_members / total_members) * 100
        
        # Calculate costs
        original_cost = members_sample['cost'].sum()
        optimized_cost = sum(a['cost'] for a in assignments if a['cost'] is not None)
        profit_loss_percentage = ((original_cost - optimized_cost) / original_cost) * 100

        # Determine network status
        if access_percentage == 100:
            network_status = "No need to change organization"
        elif access_percentage >= 95:
            network_status = "Good in provider and member access"
        else:
            network_status = "Organization must increase providers"
        
        # Count used/unused providers
        used_provider_ids = set(a['provider_id'] for a in assignments if a['provider_id'] is not None)
        total_providers = len(providers_sample)
        used_providers = len(used_provider_ids)
        unused_providers = total_providers - used_providers
        
        # Create optimization result
        optimization_result = OptimizationResult(
            dataset_members_id=members_dataset.id,
            dataset_providers_id=providers_dataset.id,
            access_percentage=access_percentage,
            original_cost=original_cost,
            optimized_cost=optimized_cost,
            profit_loss_percentage=profit_loss_percentage,
            total_members=total_members,
            served_members=served_members,
            unserved_members=unserved_members,
            total_providers=total_providers,
            used_providers=used_providers,
            unused_providers=unused_providers,
            network_status=network_status
        )
        
        # Store detailed optimization data
        optimization_data = {
            'assignments': assignments,
            'candidate_connections': len(candidate_connections),
            'source_type_analysis': optimizer.analyze_by_source_type(assignments, members_sample)
        }
        optimization_result.set_optimization_data(optimization_data)
        
        db.session.add(optimization_result)
        db.session.commit()
        
        # Store individual assignments
        for assignment in assignments:
            member_assignment = MemberProviderAssignment(
                optimization_result_id=optimization_result.id,
                member_id=assignment['member_id'],
                provider_id=assignment['provider_id'],
                distance_km=assignment['distance'],
                cost=assignment['cost'],
                provider_rating=assignment['rating'],
                is_served=assignment['provider_id'] is not None,
                member_source_type=assignment['member_source_type'],
                provider_source_type=assignment.get('provider_type')
            )
            db.session.add(member_assignment)
        
        db.session.commit()
        
        # Store result ID in session for dashboard
        session['optimization_result_id'] = optimization_result.id
        
        logger.info(f"Optimization completed. Access: {access_percentage:.2f}%, Served: {served_members}/{total_members}")
        
        return jsonify({
            'success': True,
            'optimization_id': optimization_result.id,
            'access_percentage': access_percentage,
            'served_members': served_members,
            'total_members': total_members,
            'network_status': network_status,
            'redirect': url_for('dashboard')
        })
        
    except Exception as e:
        logger.error(f"Error in network optimization: {str(e)}")
        return jsonify({'error': f'Optimization failed: {str(e)}'}), 500

@app.route('/dashboard')
@admin_required
def dashboard():
    optimization_id = session.get('optimization_result_id')
    if not optimization_id:
        flash('No optimization results found. Please run optimization first.', 'warning')
        return redirect(url_for('upload_page'))
    
    result = OptimizationResult.query.get_or_404(optimization_id)
    optimization_data = result.get_optimization_data()
    
    return render_template('dashboard.html', result=result, optimization_data=optimization_data)

@app.route('/visualization')
@admin_required
def visualization():
    optimization_id = session.get('optimization_result_id')
    if not optimization_id:
        flash('No optimization results found. Please run optimization first.', 'warning')
        return redirect(url_for('upload_page'))
    
    result = OptimizationResult.query.get_or_404(optimization_id)
    return render_template('visualization.html', result=result)

@app.route('/api/map_data')
@admin_required
def get_map_data():
    optimization_id = session.get('optimization_result_id')
    if not optimization_id:
        return jsonify({'error': 'No optimization results found'}), 404
    
    try:
        result = OptimizationResult.query.get_or_404(optimization_id)
        assignments = MemberProviderAssignment.query.filter_by(optimization_result_id=optimization_id).all()
        
        # Load datasets with same sampling logic for consistency
        members_dataset = Dataset.query.get(result.dataset_members_id)
        providers_dataset = Dataset.query.get(result.dataset_providers_id)
        
        processor = DataProcessor()
        members_path = os.path.join(app.config['UPLOAD_FOLDER'], members_dataset.filename)
        providers_path = os.path.join(app.config['UPLOAD_FOLDER'], providers_dataset.filename)
        
        members_df, _ = processor.process_members_data(members_path)
        providers_df, _ = processor.process_providers_data(providers_path)
        
        # Use same sampling logic for consistency
        if len(members_df) > 1000 or len(providers_df) > 500:
            members_df = members_df.sample(n=min(1000, len(members_df)), random_state=42)
            providers_df = providers_df.sample(n=min(500, len(providers_df)), random_state=42)
        
        # Prepare map data
        served_members = []
        unserved_members = []
        used_providers = set()
        
        for assignment in assignments:
            member_match = members_df[members_df['MemberID'] == int(assignment.member_id)]
            if member_match.empty:
                logger.warning(f"Skipping member {assignment.member_id} - not in sampled dataset")
                continue  # Skip this member safely
            member_row = member_match.iloc[0]
            member_data = {
                'id': assignment.member_id,
                'lat': float(member_row['Latitude']),
                'lng': float(member_row['Longitude']),
                'source_type': assignment.member_source_type,
                'cost': float(member_row['cost']),
                'is_served': assignment.is_served
            }
            
            if assignment.is_served:
                member_data['provider_id'] = assignment.provider_id
                member_data['distance'] = assignment.distance_km
                member_data['provider_rating'] = assignment.provider_rating
                served_members.append(member_data)
                used_providers.add(assignment.provider_id)
            else:
                unserved_members.append(member_data)
        
        # Get provider data
        providers_data = []
        for _, provider in providers_df.iterrows():
            provider_data = {
                'id': str(provider['ProviderID']),
                'lat': float(provider['Latitude']),
                'lng': float(provider['Longitude']),
                'name': provider['Location'].split(',')[0] if ',' in provider['Location'] else provider['Location'],
                'type': provider['Type'],
                'rating': provider['CMS Rating'],
                'cost': provider['Cost'],
                'is_used': str(provider['ProviderID']) in used_providers
            }
            providers_data.append(provider_data)
        
        return jsonify({
            'served_members': served_members,
            'unserved_members': unserved_members,
            'providers': providers_data,
            'stats': {
                'total_members': result.total_members,
                'served_members': result.served_members,
                'unserved_members': result.unserved_members,
                'access_percentage': result.access_percentage
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting map data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_unused_providers')
@admin_required
def download_unused_providers():
    optimization_id = session.get('optimization_result_id')
    if not optimization_id:
        return jsonify({'error': 'No optimization results found'}), 404
    
    try:
        result = OptimizationResult.query.get_or_404(optimization_id)
        
        if result.unused_providers == 0:
            flash('All providers are being used. Organization is working in good condition.', 'success')
            return redirect(url_for('dashboard'))
        
        # Get used provider IDs
        assignments = MemberProviderAssignment.query.filter_by(
            optimization_result_id=optimization_id,
            is_served=True
        ).all()
        used_provider_ids = set(a.provider_id for a in assignments if a.provider_id)
        
        # Load providers data
        providers_dataset = Dataset.query.get(result.dataset_providers_id)
        processor = DataProcessor()
        providers_path = os.path.join(app.config['UPLOAD_FOLDER'], providers_dataset.filename)
        providers_df, _ = processor.process_providers_data(providers_path)
        
        # Filter unused providers
        unused_providers_df = providers_df[~providers_df['ProviderID'].astype(str).isin(used_provider_ids)]
        
        # Select relevant columns for download
        download_columns = ['ProviderID', 'Location', 'Type', 'CMS Rating', 'Cost', 'Contact Number']
        unused_providers_export = unused_providers_df[download_columns].copy()
        
        # Rename columns for better readability
        unused_providers_export.columns = ['Provider ID', 'Provider Name & Address', 'Type', 'Rating', 'Cost', 'Contact Number']
        
        # Save to CSV
        export_filename = f'unused_providers_{optimization_id}.csv'
        export_path = os.path.join(app.config['UPLOAD_FOLDER'], export_filename)
        unused_providers_export.to_csv(export_path, index=False)
        
        return send_file(export_path, as_attachment=True, download_name=export_filename)
        
    except Exception as e:
        logger.error(f"Error downloading unused providers: {str(e)}")
        flash(f'Error generating download: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/chart_data')
@admin_required
def get_chart_data():
    optimization_id = session.get('optimization_result_id')
    if not optimization_id:
        return jsonify({'error': 'No optimization results found'}), 404
    
    try:
        result = OptimizationResult.query.get_or_404(optimization_id)
        optimization_data = result.get_optimization_data()
        
        # Source type analysis
        source_type_analysis = optimization_data.get('source_type_analysis', {})
        
        return jsonify({
            'access_chart': {
                'served': result.served_members,
                'unserved': result.unserved_members,
                'access_percentage': result.access_percentage
            },
            'cost_chart': {
                'original': result.original_cost,
                'optimized': result.optimized_cost,
                'savings': result.original_cost - result.optimized_cost,
                'profit_loss_percentage': result.profit_loss_percentage
            },
            'provider_usage': {
                'used': result.used_providers,
                'unused': result.unused_providers,
                'total': result.total_providers
            },
            'source_type_analysis': source_type_analysis
        })
        
    except Exception as e:
        logger.error(f"Error getting chart data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Member API endpoints (for external member portal integration)
@app.route('/api/member/validate', methods=['POST'])
def validate_member():
    """API endpoint for member validation (for external member portal)"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        auth_token = data.get('auth_token')
        
        # Simple validation (in production, use proper JWT tokens)
        if member_id in DEMO_MEMBER_CREDENTIALS:
            return jsonify({
                'valid': True,
                'member_id': member_id,
                'member_info': {
                    'id': member_id,
                    'name': f'Member {member_id}',
                    'type': 'Standard'
                }
            })
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        logger.error(f"Error validating member: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/member/providers', methods=['POST'])
def get_member_providers():
    """API endpoint to get providers for a specific member"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        # Validate member
        if member_id not in DEMO_MEMBER_CREDENTIALS:
            return jsonify({'error': 'Invalid member'}), 401
        
        # Get latest optimization result
        result = OptimizationResult.query.order_by(OptimizationResult.created_at.desc()).first()
        if not result:
            return jsonify({'providers': [], 'message': 'No optimization results available'})
        
        # Get member assignments
        assignments = MemberProviderAssignment.query.filter_by(
            optimization_result_id=result.id,
            member_id=member_id
        ).all()
        
        member_providers = []
        for assignment in assignments:
            if assignment.is_served:
                provider_info = {
                    'provider_id': assignment.provider_id,
                    'distance_km': assignment.distance_km,
                    'cost': assignment.cost,
                    'rating': assignment.provider_rating,
                    'type': assignment.provider_source_type
                }
                member_providers.append(provider_info)
        
        return jsonify({
            'providers': member_providers,
            'member_id': member_id,
            'total_providers': len(member_providers)
        })
        
    except Exception as e:
        logger.error(f"Error getting member providers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 500MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return render_template('500.html'), 500