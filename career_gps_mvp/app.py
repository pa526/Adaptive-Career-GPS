from flask import Flask, request, jsonify
from flask_cors import CORS
from career_gps_mvp.config import Config
from career_gps_mvp.models.database import db, User, StudentProfile, MentorProfile, UserRole

# Import Blueprints
from career_gps_mvp.routes.student_routes import student_bp
from career_gps_mvp.routes.mentor_routes import mentor_bp
from career_gps_mvp.routes.ai_routes import ai_bp
from career_gps_mvp.routes.employer_routes import employer_bp

def create_app(config_class=Config):
    """Application factory for the Career GPS MVP Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app)
    
    # Initialize Database
    db.init_app(app)
    
    # Run configuration setup
    config_class.init_app(app)
    
    # Register API Blueprints
    app.register_blueprint(student_bp)
    app.register_blueprint(mentor_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(employer_bp)
    
    # Authentication & User Management Routes
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """Register a new user and auto-generate their profile stub."""
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')  # 'STUDENT', 'MENTOR', 'EMPLOYER', 'FACULTY' (case-insensitive)
        full_name = data.get('full_name', '')
        apaar_id = data.get('apaar_id')  # Student specific

        if not email or not password or not role:
            return jsonify({'error': 'Missing required fields: email, password, role'}), 400

        # Normalize role to uppercase
        role_upper = role.upper()
        if role_upper not in UserRole.__members__:
            return jsonify({'error': 'Invalid role. Must be one of: STUDENT, MENTOR, FACULTY, EMPLOYER'}), 400

        user_role = UserRole[role_upper]

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email is already registered'}), 400

        # Check if apaar_id is unique if provided
        if apaar_id and User.query.filter_by(apaar_id=apaar_id).first():
            return jsonify({'error': 'APAAR ID is already registered'}), 400

        name_placeholder = full_name if full_name else email.split('@')[0].capitalize()

        # Create user
        new_user = User(
            email=email,
            role=user_role,
            full_name=name_placeholder,
            apaar_id=apaar_id if user_role == UserRole.STUDENT else None
        )
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.flush()  # Obtain user ID before commit to build profile

            # Auto-generate profile skeletons based on role
            if user_role == UserRole.STUDENT:
                student_profile = StudentProfile(
                    user_id=new_user.id,
                    institution_id=data.get('institution_id'),
                    current_track=data.get('current_track', ''),
                    digital_wallet_address=data.get('digital_wallet_address', '')
                )
                db.session.add(student_profile)
            elif user_role == UserRole.MENTOR:
                mentor_profile = MentorProfile(
                    user_id=new_user.id,
                    company_name=data.get('company_name', ''),
                    expertise_tags=data.get('expertise_tags', []),
                    max_mentees=data.get('max_mentees', 5)
                )
                db.session.add(mentor_profile)

            db.session.commit()
            return jsonify({
                'message': 'User registered successfully',
                'user': new_user.to_dict()
            }), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Registration failed: {str(e)}'}), 500

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Authenticate user and return role/credentials."""
        data = request.get_json() or {}
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200

    # Global Error Handlers
    @app.errorhandler(404)
    def resource_not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    # Database Initialization
    with app.app_context():
        db.create_all()
        
    return app

if __name__ == '__main__':
    # When run directly, start the development server
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
