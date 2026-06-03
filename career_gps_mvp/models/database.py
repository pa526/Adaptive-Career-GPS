import uuid
import enum
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the SQLAlchemy object
db = SQLAlchemy()

class UserRole(enum.Enum):
    STUDENT = "STUDENT"
    MENTOR = "MENTOR"
    FACULTY = "FACULTY"
    EMPLOYER = "EMPLOYER"

class NodeStatus(enum.Enum):
    LOCKED = "LOCKED"
    ACTIVE = "ACTIVE"
    STUCK = "STUCK"
    COMPLETED = "COMPLETED"

class InterventionStatus(enum.Enum):
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    RESOLVED = "RESOLVED"

class ApprenticeshipStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class User(db.Model):
    """System User model for authentication and role management using UUIDs."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    apaar_id = db.Column(db.String(100), unique=True, nullable=True)  # Nullable for non-students
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    student_profile = db.relationship(
        'StudentProfile',
        back_populates='user',
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="[StudentProfile.user_id]"
    )
    mentor_profile = db.relationship('MentorProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'apaar_id': self.apaar_id,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role.name if isinstance(self.role, UserRole) else self.role,
            'created_at': self.created_at.isoformat()
        }


class StudentProfile(db.Model):
    """Profile data for Students, linked 1:1 with Users."""
    __tablename__ = 'student_profiles'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    institution_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    current_track = db.Column(db.String(100), default="", nullable=False)
    digital_wallet_address = db.Column(db.String(255), default="", nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='student_profile', foreign_keys=[user_id])
    node_progresses = db.relationship('StudentNodeProgress', back_populates='student', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'full_name': self.user.full_name if self.user else "",
            'email': self.user.email if self.user else "",
            'institution_id': self.institution_id,
            'current_track': self.current_track,
            'digital_wallet_address': self.digital_wallet_address
        }


class MentorProfile(db.Model):
    """Profile data for Mentors, linked 1:1 with Users."""
    __tablename__ = 'mentor_profiles'

    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    company_name = db.Column(db.String(100), default="", nullable=False)
    expertise_tags = db.Column(db.JSON, default=list, nullable=False)  # JSON Array of strings
    max_mentees = db.Column(db.Integer, default=5, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='mentor_profile')
    assigned_interventions = db.relationship('AIIntervention', back_populates='assigned_mentor')

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'full_name': self.user.full_name if self.user else "",
            'email': self.user.email if self.user else "",
            'company_name': self.company_name,
            'expertise_tags': self.expertise_tags or [],
            'max_mentees': self.max_mentees
        }


class LearningNode(db.Model):
    """Static learning roadmaps and skills curriculum."""
    __tablename__ = 'learning_nodes'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    track_name = db.Column(db.String(100), nullable=False)
    prerequisites = db.Column(db.JSON, default=list, nullable=False)  # JSON Array of prerequisite Node IDs

    # Relationships
    progress_records = db.relationship('StudentNodeProgress', back_populates='node', cascade="all, delete-orphan")
    apprenticeships = db.relationship('EmployerMicroApprenticeship', back_populates='required_skill_node', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'track_name': self.track_name,
            'prerequisites': self.prerequisites or []
        }


class StudentNodeProgress(db.Model):
    """Core state tracker mapping students to Learning Nodes."""
    __tablename__ = 'student_node_progress'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('student_profiles.user_id', ondelete='CASCADE'), nullable=False)
    node_id = db.Column(db.String(36), db.ForeignKey('learning_nodes.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum(NodeStatus), default=NodeStatus.LOCKED, nullable=False)
    stagnation_days = db.Column(db.Integer, default=0, nullable=False)
    score = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    student = db.relationship('StudentProfile', back_populates='node_progresses')
    node = db.relationship('LearningNode', back_populates='progress_records')
    interventions = db.relationship('AIIntervention', back_populates='progress', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'node_id': self.node_id,
            'node_title': self.node.title if self.node else "",
            'track_name': self.node.track_name if self.node else "",
            'status': self.status.name if isinstance(self.status, NodeStatus) else self.status,
            'stagnation_days': self.stagnation_days,
            'score': self.score
        }


class AIIntervention(db.Model):
    """System to support student recovery loops when stuck."""
    __tablename__ = 'ai_interventions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    progress_id = db.Column(db.String(36), db.ForeignKey('student_node_progress.id', ondelete='CASCADE'), nullable=False)
    identified_gap = db.Column(db.Text, nullable=False)
    generated_micro_tasks = db.Column(db.JSON, default=dict, nullable=False)  # Gemini output format
    assigned_mentor_id = db.Column(db.String(36), db.ForeignKey('mentor_profiles.user_id', ondelete='SET NULL'), nullable=True)
    resolution_status = db.Column(db.Enum(InterventionStatus), default=InterventionStatus.PENDING, nullable=False)

    # Relationships
    progress = db.relationship('StudentNodeProgress', back_populates='interventions')
    assigned_mentor = db.relationship('MentorProfile', back_populates='assigned_interventions')

    def to_dict(self):
        return {
            'id': self.id,
            'progress_id': self.progress_id,
            'node_title': self.progress.node.title if (self.progress and self.progress.node) else "",
            'student_id': self.progress.student_id if self.progress else "",
            'student_name': self.progress.student.user.full_name if (self.progress and self.progress.student and self.progress.student.user) else "",
            'identified_gap': self.identified_gap,
            'generated_micro_tasks': self.generated_micro_tasks or {},
            'assigned_mentor_id': self.assigned_mentor_id,
            'assigned_mentor_name': self.assigned_mentor.user.full_name if (self.assigned_mentor and self.assigned_mentor.user) else None,
            'resolution_status': self.resolution_status.name if isinstance(self.resolution_status, InterventionStatus) else self.resolution_status
        }


class EmployerMicroApprenticeship(db.Model):
    """Employer-posted micro-tasks linked to learning nodes/skills."""
    __tablename__ = 'employer_micro_apprenticeships'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    employer_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    required_skill_node_id = db.Column(db.String(36), db.ForeignKey('learning_nodes.id', ondelete='CASCADE'), nullable=False)
    task_title = db.Column(db.String(100), nullable=False)
    stipend_amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(ApprenticeshipStatus), default=ApprenticeshipStatus.OPEN, nullable=False)

    # Relationships
    employer = db.relationship('User')
    required_skill_node = db.relationship('LearningNode', back_populates='apprenticeships')

    def to_dict(self):
        return {
            'id': self.id,
            'employer_id': self.employer_id,
            'employer_name': self.employer.full_name if self.employer else "",
            'required_skill_node_id': self.required_skill_node_id,
            'required_skill_node_title': self.required_skill_node.title if self.required_skill_node else "",
            'task_title': self.task_title,
            'stipend_amount': self.stipend_amount,
            'status': self.status.name if isinstance(self.status, ApprenticeshipStatus) else self.status
        }
