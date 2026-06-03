from flask import Blueprint, request, jsonify
from career_gps_mvp.models.database import (
    db, User, UserRole, MentorProfile, AIIntervention, StudentNodeProgress,
    NodeStatus, InterventionStatus
)

mentor_bp = Blueprint('mentor', __name__)

@mentor_bp.route('/api/mentor/profile', methods=['POST'])
def save_mentor_profile():
    """Create or update a mentor profile."""
    data = request.get_json() or {}
    user_id = data.get('user_id')
    full_name = data.get('full_name')
    company_name = data.get('company_name', '')
    expertise_tags = data.get('expertise_tags', [])
    max_mentees = data.get('max_mentees', 5)

    if not user_id:
        return jsonify({'error': 'Missing required fields: user_id'}), 400

    try:
        max_mentees = int(max_mentees)
    except ValueError:
        return jsonify({'error': 'max_mentees must be an integer'}), 400

    # Ensure user exists and is a mentor
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != UserRole.MENTOR:
        return jsonify({'error': 'User is not registered as a mentor'}), 400

    # Update User table full name if provided
    if full_name:
        user.full_name = full_name

    # Check if profile already exists
    profile = MentorProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile.company_name = company_name
        profile.expertise_tags = expertise_tags
        profile.max_mentees = max_mentees
    else:
        profile = MentorProfile(
            user_id=user_id,
            company_name=company_name,
            expertise_tags=expertise_tags,
            max_mentees=max_mentees
        )
        db.session.add(profile)

    try:
        db.session.commit()
        return jsonify({'message': 'Profile saved successfully', 'profile': profile.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@mentor_bp.route('/api/mentor/profile/<string:user_id>', methods=['GET'])
def get_mentor_profile(user_id):
    """Retrieve the mentor profile by user ID."""
    profile = MentorProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({'error': 'Mentor profile not found'}), 404
    return jsonify(profile.to_dict()), 200


@mentor_bp.route('/api/mentor/interventions', methods=['GET'])
def get_interventions():
    """Retrieve the list of AI interventions with optional status & mentor filters."""
    status_str = request.args.get('status')
    assigned_mentor_id = request.args.get('assigned_mentor_id')
    unassigned_only = request.args.get('unassigned_only', 'false').lower() == 'true'

    query = AIIntervention.query

    if status_str:
        status_upper = status_str.upper()
        if status_upper in InterventionStatus.__members__:
            query = query.filter(AIIntervention.resolution_status == InterventionStatus[status_upper])
        else:
            return jsonify({'error': 'Invalid status filter. Must be one of: PENDING, REVIEWING, RESOLVED'}), 400

    if unassigned_only:
        query = query.filter(AIIntervention.assigned_mentor_id.is_(None))
    elif assigned_mentor_id:
        query = query.filter(AIIntervention.assigned_mentor_id == assigned_mentor_id)

    interventions = query.all()
    return jsonify([i.to_dict() for i in interventions]), 200


@mentor_bp.route('/api/mentor/interventions/<string:intervention_id>/assign', methods=['POST'])
def assign_intervention(intervention_id):
    """Allow a mentor to claim/assign themselves to an AI intervention."""
    data = request.get_json() or {}
    mentor_user_id = data.get('mentor_user_id')

    if not mentor_user_id:
        return jsonify({'error': 'Missing required field: mentor_user_id'}), 400

    # Ensure mentor exists
    mentor = MentorProfile.query.filter_by(user_id=mentor_user_id).first()
    if not mentor:
        return jsonify({'error': 'Mentor profile not found'}), 404

    # Ensure intervention exists
    intervention = AIIntervention.query.filter_by(id=intervention_id).first()
    if not intervention:
        return jsonify({'error': 'AI Intervention not found'}), 404

    if intervention.resolution_status == InterventionStatus.RESOLVED:
        return jsonify({'error': 'Cannot claim an already resolved intervention'}), 400

    # Assign and mark as REVIEWING
    intervention.assigned_mentor_id = mentor.user_id
    intervention.resolution_status = InterventionStatus.REVIEWING

    try:
        db.session.commit()
        return jsonify({
            'message': 'AI Intervention successfully claimed by mentor.',
            'intervention': intervention.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@mentor_bp.route('/api/mentor/interventions/<string:intervention_id>/resolve', methods=['POST'])
def resolve_intervention(intervention_id):
    """Allow a mentor to resolve an intervention, releasing the student progress back to ACTIVE or COMPLETED."""
    data = request.get_json() or {}
    mentor_user_id = data.get('mentor_user_id')
    next_node_status = data.get('next_status', 'ACTIVE')  # 'ACTIVE' or 'COMPLETED'

    if not mentor_user_id:
        return jsonify({'error': 'Missing required field: mentor_user_id'}), 400

    next_status_upper = next_node_status.upper()
    if next_status_upper not in ['ACTIVE', 'COMPLETED']:
        return jsonify({'error': 'Invalid next_status. Must be ACTIVE or COMPLETED'}), 400

    # Ensure mentor exists
    mentor = MentorProfile.query.filter_by(user_id=mentor_user_id).first()
    if not mentor:
        return jsonify({'error': 'Mentor profile not found'}), 404

    # Ensure intervention exists
    intervention = AIIntervention.query.filter_by(id=intervention_id).first()
    if not intervention:
        return jsonify({'error': 'AI Intervention not found'}), 404

    # Update resolution status
    intervention.resolution_status = InterventionStatus.RESOLVED
    intervention.assigned_mentor_id = mentor.user_id  # In case not already assigned

    # Update the student's progress status back to ACTIVE or COMPLETED
    progress = StudentNodeProgress.query.filter_by(id=intervention.progress_id).first()
    if progress:
        progress.status = NodeStatus[next_status_upper]
        progress.stagnation_days = 0  # Reset stagnation

    try:
        db.session.commit()
        return jsonify({
            'message': 'AI Intervention resolved successfully. Student node status updated.',
            'intervention': intervention.to_dict(),
            'student_progress': progress.to_dict() if progress else None
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
