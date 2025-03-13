
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import Session, Payment, Package, User

logger = logging.getLogger(__name__)

def get_user_usage_stats(user_id, days=30):
    """Get usage statistics for a specific user"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get total session time
    total_time = db.session.query(
        func.sum(Session.end_time - Session.start_time)
    ).filter(
        Session.user_id == user_id,
        Session.start_time >= start_date
    ).scalar()
    
    # Get total data used
    total_data = db.session.query(
        func.sum(Session.data_used_mb)
    ).filter(
        Session.user_id == user_id,
        Session.start_time >= start_date
    ).scalar()
    
    # Get total payments
    total_spent = db.session.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.user_id == user_id,
        Payment.status == 'completed',
        Payment.created_at >= start_date
    ).scalar()
    
    # Get session count
    session_count = Session.query.filter(
        Session.user_id == user_id,
        Session.start_time >= start_date
    ).count()
    
    # Format time (total seconds -> hours/minutes)
    hours = 0
    minutes = 0
    if total_time:
        total_seconds = total_time.total_seconds()
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, _ = divmod(remainder, 60)
    
    return {
        'total_time': {
            'hours': hours,
            'minutes': minutes,
            'formatted': f"{hours}h {minutes}m"
        },
        'total_data': total_data or 0,
        'total_spent': total_spent or 0,
        'session_count': session_count or 0
    }

def get_usage_history(user_id, days=30):
    """Get daily usage history for charts"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get daily session times
    daily_sessions = db.session.query(
        func.date(Session.start_time).label('date'),
        func.sum(func.julianday(Session.end_time) - func.julianday(Session.start_time)).label('hours')
    ).filter(
        Session.user_id == user_id,
        Session.start_time >= start_date
    ).group_by(
        func.date(Session.start_time)
    ).all()
    
    # Get daily data usage
    daily_data = db.session.query(
        func.date(Session.start_time).label('date'),
        func.sum(Session.data_used_mb).label('data')
    ).filter(
        Session.user_id == user_id,
        Session.start_time >= start_date
    ).group_by(
        func.date(Session.start_time)
    ).all()
    
    # Format for charts
    dates = []
    hours = []
    data_usage = []
    
    # Create a date range for all days
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        dates.append(date)
        hours.append(0)
        data_usage.append(0)
    
    # Fill in actual data
    for session in daily_sessions:
        date_str = session.date
        try:
            idx = dates.index(date_str)
            hours[idx] = round(session.hours * 24, 2)  # Convert from Julian day fraction to hours
        except ValueError:
            pass
    
    for usage in daily_data:
        date_str = usage.date
        try:
            idx = dates.index(date_str)
            data_usage[idx] = round(usage.data, 2)
        except ValueError:
            pass
    
    return {
        'dates': dates,
        'hours': hours,
        'data_usage': data_usage
    }

def get_popular_packages(days=30):
    """Get most popular packages based on purchases"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    popular_packages = db.session.query(
        Package.id,
        Package.name,
        func.count(Payment.id).label('purchase_count')
    ).join(
        Payment, Payment.package_id == Package.id
    ).filter(
        Payment.status == 'completed',
        Payment.created_at >= start_date
    ).group_by(
        Package.id
    ).order_by(
        func.count(Payment.id).desc()
    ).limit(5).all()
    
    return popular_packages
