from flask import Blueprint, request, jsonify
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from src.database import SessionLocal
import jwt
from src.models import User


JWT_SECRET = "your-jwt-secret-key-replace-this"  # Change this in production
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours in seconds


auth_router = Blueprint("auth", __name__)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            db = SessionLocal()
            current_user = db.query(User).filter_by(user_id=data['user_id']).first()
            db.close()
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
                
        except Exception as e:
            return jsonify({'message': 'Token is invalid', 'error': str(e)}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated


@auth_router.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(key in data for key in ['name', 'email', 'password', 'confirmPassword']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if passwords match
    if data['password'] != data['confirmPassword']:
        return jsonify({'message': 'Passwords do not match'}), 400
    
    db = SessionLocal()
    
    # Check if user already exists
    existing_user = db.query(User).filter_by(email=data['email']).first()
    if existing_user:
        db.close()
        return jsonify({'message': 'User already exists'}), 409
    
    # Create new user
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        name=data['name'],
        email=data['email'], 
        password_hash=hashed_password
    )
    
    try:
        db.add(new_user)
        db.commit()
        
        # Generate token
        token = jwt.encode({
            'user_id': new_user.user_id,
            'email': new_user.email,
            'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
        }, JWT_SECRET, algorithm="HS256")
        
        db.close()
        
        return jsonify({
            'message': 'User created successfully',
            'token': token,
            'user': {
                'user_id': new_user.user_id,
                'name': new_user.name,
                'email': new_user.email
            }
        }), 201
        
    except Exception as e:
        db.rollback()
        db.close()
        print(e)
        return jsonify({'message': 'Error creating user', 'error': str(e)}), 500


@auth_router.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if required fields are present
    if not all(key in data for key in ['email', 'password']):
        return jsonify({'message': 'Missing required fields'}), 400
    
    db = SessionLocal()
    
    # Find user by email
    user = db.query(User).filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        db.close()
        return jsonify({'message': 'Invalid email or password'}), 401
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate token
    token = jwt.encode({
        'user_id': user.user_id,
        'email': user.email,
        'exp': datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }, JWT_SECRET, algorithm="HS256")
    
    db.close()
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': {
            'user_id': user.user_id,
            'name': user.name,
            'email': user.email
        }
    }), 200

@auth_router.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    return jsonify({
        'user_id': current_user.user_id,
        'name': current_user.name,
        'email': current_user.email
    }), 200

@auth_router.route('/logout', methods=['POST'])
def logout():
    # JWT tokens are stateless, so we don't need to do anything server-side
    # The client will remove the token
    return jsonify({'message': 'Logged out successfully'}), 200


