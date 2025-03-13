
import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from models import FamilyDevice, Package, Payment, Session
from datetime import datetime, timedelta
from utils.mikrotik import mikrotik

family_bp = Blueprint('family', __name__, url_prefix='/family')
logger = logging.getLogger(__name__)

@family_bp.route('/')
@login_required
def index():
    """Family plan dashboard"""
    # Get user's managed devices
    managed_devices = FamilyDevice.query.filter_by(user_id=current_user.id).all()
    
    # Get available family plans
    family_plans = Package.query.filter_by(
        is_active=True, 
        is_family_plan=True
    ).all()
    
    # Mark the most popular plan
    if family_plans:
        # Find the most purchased plan
        most_purchased = db.session.query(
            Package.id, 
            db.func.count(Payment.id).label('count')
        ).join(
            Payment, Payment.package_id == Package.id
        ).filter(
            Package.is_family_plan == True,
            Payment.status == 'completed'
        ).group_by(Package.id).order_by(
            db.desc('count')
        ).first()
        
        if most_purchased:
            for plan in family_plans:
                plan.is_popular = (plan.id == most_purchased[0])
    
    return render_template(
        'family_plan.html',
        managed_devices=managed_devices,
        family_plans=family_plans
    )

@family_bp.route('/device/add', methods=['POST'])
@login_required
def add_device():
    """Add a new device to family plan"""
    name = request.form.get('name')
    mac_address = request.form.get('mac_address')
    data_limit_mb = request.form.get('data_limit_mb')
    
    if not name or not mac_address:
        flash('Device name and MAC address are required', 'danger')
        return redirect(url_for('family.index'))
    
    # Normalize MAC address format
    mac_address = mac_address.upper()
    
    # Check if device already exists
    existing_device = FamilyDevice.query.filter_by(mac_address=mac_address).first()
    if existing_device:
        flash('This device is already registered in a family plan', 'danger')
        return redirect(url_for('family.index'))
    
    # Check how many devices the user already has
    device_count = FamilyDevice.query.filter_by(user_id=current_user.id).count()
    max_devices = 5  # Set a default maximum
    
    # Check if user has an active family plan and get its device limit
    active_session = Session.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).join(Package).filter(
        Package.is_family_plan == True
    ).first()
    
    if active_session:
        max_devices = active_session.package.device_limit
    
    if device_count >= max_devices:
        flash(f'You have reached the maximum of {max_devices} devices for your family plan', 'danger')
        return redirect(url_for('family.index'))
    
    # Create new device
    device = FamilyDevice(
        user_id=current_user.id,
        name=name,
        mac_address=mac_address,
        data_limit_mb=data_limit_mb if data_limit_mb else None
    )
    
    db.session.add(device)
    db.session.commit()
    
    flash('Device added to your family plan successfully', 'success')
    return redirect(url_for('family.index'))

@family_bp.route('/device/<int:device_id>')
@login_required
def get_device(device_id):
    """Get device details as JSON"""
    device = FamilyDevice.query.get_or_404(device_id)
    
    # Check ownership
    if device.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    return jsonify({
        'success': True,
        'device': {
            'id': device.id,
            'name': device.name,
            'mac_address': device.mac_address,
            'data_limit_mb': device.data_limit_mb
        }
    })

@family_bp.route('/device/<int:device_id>/edit', methods=['POST'])
@login_required
def edit_device(device_id):
    """Edit a family device"""
    device = FamilyDevice.query.get_or_404(device_id)
    
    # Check ownership
    if device.user_id != current_user.id:
        flash('You do not have permission to edit this device', 'danger')
        return redirect(url_for('family.index'))
    
    name = request.form.get('name')
    mac_address = request.form.get('mac_address')
    data_limit_mb = request.form.get('data_limit_mb')
    
    if not name or not mac_address:
        flash('Device name and MAC address are required', 'danger')
        return redirect(url_for('family.index'))
    
    # Normalize MAC address format
    mac_address = mac_address.upper()
    
    # Check if MAC address is already used by another device
    existing_device = FamilyDevice.query.filter(
        FamilyDevice.mac_address == mac_address, 
        FamilyDevice.id != device_id
    ).first()
    
    if existing_device:
        flash('This MAC address is already used by another device', 'danger')
        return redirect(url_for('family.index'))
    
    # Update device
    device.name = name
    device.mac_address = mac_address
    device.data_limit_mb = data_limit_mb if data_limit_mb else None
    
    db.session.commit()
    
    flash('Device updated successfully', 'success')
    return redirect(url_for('family.index'))

@family_bp.route('/device/<int:device_id>/remove', methods=['POST'])
@login_required
def remove_device(device_id):
    """Remove a device from family plan"""
    device = FamilyDevice.query.get_or_404(device_id)
    
    # Check ownership
    if device.user_id != current_user.id:
        flash('You do not have permission to remove this device', 'danger')
        return redirect(url_for('family.index'))
    
    # Remove device from MikroTik if it's connected
    if device.mikrotik_username:
        mikrotik.disconnect_user(device.mikrotik_username)
        mikrotik.remove_user(device.mikrotik_username)
    
    # Delete device
    db.session.delete(device)
    db.session.commit()
    
    flash('Device removed from your family plan', 'success')
    return redirect(url_for('family.index'))

@family_bp.route('/purchase/<int:plan_id>')
@login_required
def purchase(plan_id):
    """Redirect to payment for family plan"""
    plan = Package.query.get_or_404(plan_id)
    
    if not plan.is_family_plan:
        flash('Invalid family plan selected', 'danger')
        return redirect(url_for('family.index'))
    
    # Redirect to payment page with plan ID
    return redirect(url_for('payment.checkout', package_id=plan_id))
