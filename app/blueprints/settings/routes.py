from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.blueprints.settings import settings_bp
from app.blueprints.settings.forms import ChangePasswordForm, EditProfileForm
from app.models import User, Settings

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    profile_form = EditProfileForm(username=current_user.username, email=current_user.email)
    password_form = ChangePasswordForm()
    
    # Handle Profile Update
    if 'email' in request.form and profile_form.validate_on_submit():
        current_user.username = profile_form.username.data
        current_user.email = profile_form.email.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings.index'))
        
    # Handle Password Update
    if 'old_password' in request.form and password_form.validate_on_submit():
        if current_user.check_password(password_form.old_password.data):
            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('settings.index'))
        else:
            flash('Incorrect current password.', 'danger')
            return redirect(url_for('settings.index'))

    # Load system settings
    hotel_name = Settings.get('hotel_name', 'Hotel Saiprasad')
    hotel_address = Settings.get('hotel_address', '')
    hotel_phone = Settings.get('hotel_phone', '')
    
    return render_template(
        'settings/index.html',
        profile_form=profile_form,
        password_form=password_form,
        hotel_name=hotel_name,
        hotel_address=hotel_address,
        hotel_phone=hotel_phone
    )


@settings_bp.route('/save_system_settings', methods=['POST'])
@login_required
def save_system_settings():
    if current_user.role != 'Admin':
        flash('Only administrators can edit system settings.', 'danger')
        return redirect(url_for('settings.index'))
        
    hotel_name = request.form.get('hotel_name')
    hotel_address = request.form.get('hotel_address')
    hotel_phone = request.form.get('hotel_phone')
    
    if hotel_name:
        Settings.set('hotel_name', hotel_name)
    Settings.set('hotel_address', hotel_address)
    Settings.set('hotel_phone', hotel_phone)
    db.session.commit()
    
    flash('System settings updated successfully!', 'success')
    return redirect(url_for('settings.index'))


@settings_bp.route('/users')
@login_required
def users():
    flash('User management is disabled as only admin login is active.', 'warning')
    return redirect(url_for('settings.index'))


@settings_bp.route('/users/toggle/<int:user_id>')
@login_required
def toggle_user(user_id):
    flash('User management is disabled as only admin login is active.', 'warning')
    return redirect(url_for('settings.index'))
