from flask import Blueprint, request, jsonify
from career_gps_mvp.models.database import (
    db, StudentProfile, User, UserRole, LearningNode, StudentNodeProgress,
    NodeStatus, AIIntervention, InterventionStatus, EmployerMicroApprenticeship, ApprenticeshipStatus
)

student_bp = Blueprint('student', __name__)

@student_bp.route('/api/students/profile', methods=['POST'])
def save_student_profile():
    """Create or update a student profile."""
    data = request.get_json() or {}
    
    user_id = data.get('user_id')
    full_name = data.get('full_name')
    institution_id = data.get('institution_id')
    current_track = data.get('current_track', '')
    digital_wallet_address = data.get('digital_wallet_address', '')

    if not user_id:
        return jsonify({'error': 'Missing required fields: user_id'}), 400

    # Ensure user exists and is a student
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != UserRole.STUDENT:
        return jsonify({'error': 'User is not registered as a student'}), 400

    # If institution_id is provided, verify it is a faculty member
    if institution_id:
        inst_user = User.query.filter_by(id=institution_id).first()
        if not inst_user:
            return jsonify({'error': 'Institution (Faculty) user not found'}), 404
        if inst_user.role != UserRole.FACULTY:
            return jsonify({'error': 'Institution user must have the role FACULTY'}), 400

    # Update User table full name if provided
    if full_name:
        user.full_name = full_name

    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.institution_id = institution_id
        profile.current_track = current_track
        profile.digital_wallet_address = digital_wallet_address
    else:
        profile = StudentProfile(
            user_id=user_id,
            institution_id=institution_id,
            current_track=current_track,
            digital_wallet_address=digital_wallet_address
        )
        db.session.add(profile)

    try:
        db.session.commit()
        return jsonify({'message': 'Profile saved successfully', 'profile': profile.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@student_bp.route('/api/students/profile/<string:user_id>', methods=['GET'])
def get_student_profile(user_id):
    """Retrieve the student profile by user ID."""
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Student profile not found'}), 404
    return jsonify(profile.to_dict()), 200


@student_bp.route('/api/students/dashboard/<string:user_id>', methods=['GET'])
def get_student_dashboard(user_id):
    """Get aggregate metrics, progress, and matched micro-apprenticeships for student dashboard."""
    profile = StudentProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Student profile not found'}), 404

    # Fetch all node progress
    progress_records = StudentNodeProgress.query.filter_by(student_id=user_id).all()
    progress_list = [p.to_dict() for p in progress_records]

    # Fetch active AI Interventions
    active_interventions = AIIntervention.query.join(StudentNodeProgress).filter(
        StudentNodeProgress.student_id == user_id,
        AIIntervention.resolution_status.in_([InterventionStatus.PENDING, InterventionStatus.REVIEWING])
    ).all()
    interventions_list = [i.to_dict() for i in active_interventions]

    # Calculate completed node IDs
    completed_node_ids = [p.node_id for p in progress_records if p.status == NodeStatus.COMPLETED]

    # Fetch matched micro-apprenticeships (OPEN, and required skill node is COMPLETED by this student)
    matched = []
    if completed_node_ids:
        matched_jobs = EmployerMicroApprenticeship.query.filter(
            EmployerMicroApprenticeship.required_skill_node_id.in_(completed_node_ids),
            EmployerMicroApprenticeship.status == ApprenticeshipStatus.OPEN
        ).all()
        matched = [job.to_dict() for job in matched_jobs]

    return jsonify({
        'student_profile': profile.to_dict(),
        'node_progress': progress_list,
        'active_interventions': interventions_list,
        'matched_apprenticeships': matched
    }), 200


@student_bp.route('/api/students/progress', methods=['POST'])
def update_node_progress():
    """Create or update a student's learning node progress status."""
    data = request.get_json() or {}
    student_id = data.get('student_id')
    node_id = data.get('node_id')
    status_str = data.get('status')
    stagnation_days = data.get('stagnation_days', 0)
    score = data.get('score', 0)

    if not student_id or not node_id or not status_str:
        return jsonify({'error': 'Missing required fields: student_id, node_id, status'}), 400

    # Validate status enum
    status_upper = status_str.upper()
    if status_upper not in NodeStatus.__members__:
        return jsonify({'error': 'Invalid status. Must be: LOCKED, ACTIVE, STUCK, COMPLETED'}), 400

    node_status = NodeStatus[status_upper]

    # Ensure student profile exists
    student = StudentProfile.query.filter_by(user_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404

    # Ensure node exists
    node = LearningNode.query.filter_by(id=node_id).first()
    if not node:
        return jsonify({'error': 'Learning node not found'}), 404

    progress = StudentNodeProgress.query.filter_by(student_id=student_id, node_id=node_id).first()
    if progress:
        progress.status = node_status
        progress.stagnation_days = stagnation_days
        progress.score = score
    else:
        progress = StudentNodeProgress(
            student_id=student_id,
            node_id=node_id,
            status=node_status,
            stagnation_days=stagnation_days,
            score=score
        )
        db.session.add(progress)

    try:
        db.session.commit()
        return jsonify({
            'message': 'Node progress updated successfully',
            'progress': progress.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@student_bp.route('/api/students/progress/<string:user_id>', methods=['GET'])
def get_student_progress(user_id):
    """Retrieve progress of all nodes for a student."""
    student = StudentProfile.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404

    progress_records = StudentNodeProgress.query.filter_by(student_id=user_id).all()
    return jsonify([p.to_dict() for p in progress_records]), 200


@student_bp.route('/api/students/learning_nodes', methods=['POST'])
def create_learning_node():
    """Create a new learning node (utility for setup/testing)."""
    data = request.get_json() or {}
    title = data.get('title')
    track_name = data.get('track_name')
    prerequisites = data.get('prerequisites', [])

    if not title or not track_name:
        return jsonify({'error': 'Missing required fields: title, track_name'}), 400

    new_node = LearningNode(
        title=title,
        track_name=track_name,
        prerequisites=prerequisites
    )

    try:
        db.session.add(new_node)
        db.session.commit()
        return jsonify({
            'message': 'Learning node created successfully',
            'node': new_node.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@student_bp.route('/api/students/learning_nodes', methods=['GET'])
def get_learning_nodes():
    """List all learning nodes."""
    track = request.args.get('track_name')
    if track:
        nodes = LearningNode.query.filter_by(track_name=track).all()
    else:
        nodes = LearningNode.query.all()
    return jsonify([n.to_dict() for n in nodes]), 200
