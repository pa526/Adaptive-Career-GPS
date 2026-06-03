from flask import Blueprint, request, jsonify
from career_gps_mvp.models.database import (
    db, User, UserRole, LearningNode, StudentProfile, StudentNodeProgress, NodeStatus,
    EmployerMicroApprenticeship, ApprenticeshipStatus
)

employer_bp = Blueprint('employer', __name__)

@employer_bp.route('/api/employer/apprenticeships', methods=['POST'])
def create_apprenticeship():
    """Create a new micro-apprenticeship."""
    data = request.get_json() or {}
    employer_id = data.get('employer_id')
    required_skill_node_id = data.get('required_skill_node_id')
    task_title = data.get('task_title')
    stipend_amount = data.get('stipend_amount')

    if not employer_id or not required_skill_node_id or not task_title or stipend_amount is None:
        return jsonify({'error': 'Missing required fields: employer_id, required_skill_node_id, task_title, stipend_amount'}), 400

    try:
        stipend_amount = int(stipend_amount)
    except ValueError:
        return jsonify({'error': 'stipend_amount must be an integer'}), 400

    # Verify employer user exists and is an employer
    employer = User.query.filter_by(id=employer_id).first()
    if not employer:
        return jsonify({'error': 'Employer user not found'}), 404
    if employer.role != UserRole.EMPLOYER:
        return jsonify({'error': 'User is not registered as an employer'}), 400

    # Verify skill node exists
    node = LearningNode.query.filter_by(id=required_skill_node_id).first()
    if not node:
        return jsonify({'error': 'Learning node not found'}), 404

    # Create apprenticeship
    new_apprenticeship = EmployerMicroApprenticeship(
        employer_id=employer_id,
        required_skill_node_id=required_skill_node_id,
        task_title=task_title,
        stipend_amount=stipend_amount,
        status=ApprenticeshipStatus.OPEN
    )

    try:
        db.session.add(new_apprenticeship)
        db.session.commit()
        return jsonify({
            'message': 'Micro-apprenticeship created successfully',
            'apprenticeship': new_apprenticeship.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@employer_bp.route('/api/employer/apprenticeships', methods=['GET'])
def get_apprenticeships():
    """List all micro-apprenticeships with optional filters."""
    employer_id = request.args.get('employer_id')
    status_str = request.args.get('status')

    query = EmployerMicroApprenticeship.query

    if employer_id:
        query = query.filter_by(employer_id=employer_id)

    if status_str:
        status_upper = status_str.upper()
        if status_upper in ApprenticeshipStatus.__members__:
            query = query.filter_by(status=ApprenticeshipStatus[status_upper])
        else:
            return jsonify({'error': f'Invalid status filter. Must be one of: OPEN, IN_PROGRESS, COMPLETED'}), 400

    apprenticeships = query.all()
    return jsonify([a.to_dict() for a in apprenticeships]), 200


@employer_bp.route('/api/employer/apprenticeships/<string:apprenticeship_id>/status', methods=['POST'])
def update_apprenticeship_status(apprenticeship_id):
    """Update the status of a micro-apprenticeship."""
    data = request.get_json() or {}
    status_str = data.get('status')

    if not status_str:
        return jsonify({'error': 'Missing required field: status'}), 400

    status_upper = status_str.upper()
    if status_upper not in ApprenticeshipStatus.__members__:
        return jsonify({'error': 'Invalid status. Must be one of: OPEN, IN_PROGRESS, COMPLETED'}), 400

    new_status = ApprenticeshipStatus[status_upper]

    apprenticeship = EmployerMicroApprenticeship.query.filter_by(id=apprenticeship_id).first()
    if not apprenticeship:
        return jsonify({'error': 'Micro-apprenticeship not found'}), 404

    apprenticeship.status = new_status

    try:
        db.session.commit()
        return jsonify({
            'message': 'Apprenticeship status updated successfully',
            'apprenticeship': apprenticeship.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


@employer_bp.route('/api/employer/apprenticeships/matched/<string:student_user_id>', methods=['GET'])
def get_matched_apprenticeships(student_user_id):
    """Retrieve micro-apprenticeships matching completed learning nodes of a student."""
    student = StudentProfile.query.filter_by(user_id=student_user_id).first()
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404

    # Get completed learning nodes for the student
    completed_progresses = StudentNodeProgress.query.filter_by(
        student_id=student_user_id,
        status=NodeStatus.COMPLETED
    ).all()

    completed_node_ids = [p.node_id for p in completed_progresses]

    # Find open micro-apprenticeships requiring those skill nodes
    if not completed_node_ids:
        # If no nodes completed, return empty list
        return jsonify([]), 200

    matched = EmployerMicroApprenticeship.query.filter(
        EmployerMicroApprenticeship.required_skill_node_id.in_(completed_node_ids),
        EmployerMicroApprenticeship.status == ApprenticeshipStatus.OPEN
    ).all()

    return jsonify([a.to_dict() for a in matched]), 200
