import os
import unittest
import json
from career_gps_mvp.app import create_app
from career_gps_mvp.models.database import (
    db, User, StudentProfile, MentorProfile, LearningNode, StudentNodeProgress,
    NodeStatus, AIIntervention, InterventionStatus, EmployerMicroApprenticeship,
    ApprenticeshipStatus
)

class TestCareerGPSBackend(unittest.TestCase):
    def setUp(self):
        # Configure app to use a test SQLite database
        self.db_path = "test_career_gps.db"
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{self.db_path}"
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_complete_workflow(self):
        # 1. Register a student
        student_reg_data = {
            'email': 'student@example.com',
            'password': 'password123',
            'role': 'student',
            'full_name': 'Parth Student',
            'apaar_id': 'APAAR-12345'
        }
        res = self.client.post('/api/auth/register', json=student_reg_data)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data['user']['email'], 'student@example.com')
        self.assertEqual(data['user']['role'], 'STUDENT')
        self.assertEqual(data['user']['apaar_id'], 'APAAR-12345')
        self.assertEqual(len(data['user']['id']), 36) # UUID string length
        student_user_id = data['user']['id']

        # Verify profile skeleton created
        res = self.client.get(f'/api/students/profile/{student_user_id}')
        self.assertEqual(res.status_code, 200)
        profile_data = json.loads(res.data)
        self.assertEqual(profile_data['full_name'], 'Parth Student')
        self.assertEqual(profile_data['current_track'], '')

        # 2. Register a mentor
        mentor_reg_data = {
            'email': 'mentor@example.com',
            'password': 'password123',
            'role': 'mentor',
            'full_name': 'Hitesh Mentor',
            'company_name': 'Google DeepMind',
            'expertise_tags': ['Python', 'SQL', 'Flask'],
            'max_mentees': 10
        }
        res = self.client.post('/api/auth/register', json=mentor_reg_data)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        mentor_user_id = data['user']['id']
        self.assertEqual(data['user']['role'], 'MENTOR')

        # Verify mentor profile skeleton created
        res = self.client.get(f'/api/mentor/profile/{mentor_user_id}')
        self.assertEqual(res.status_code, 200)
        mentor_profile_data = json.loads(res.data)
        self.assertEqual(mentor_profile_data['company_name'], 'Google DeepMind')
        self.assertEqual(mentor_profile_data['expertise_tags'], ['Python', 'SQL', 'Flask'])
        self.assertEqual(mentor_profile_data['max_mentees'], 10)

        # 3. Register faculty
        faculty_reg_data = {
            'email': 'faculty@example.com',
            'password': 'password123',
            'role': 'faculty',
            'full_name': 'Professor Albus'
        }
        res = self.client.post('/api/auth/register', json=faculty_reg_data)
        self.assertEqual(res.status_code, 201)
        faculty_user_id = json.loads(res.data)['user']['id']

        # 4. Register employer
        employer_reg_data = {
            'email': 'employer@example.com',
            'password': 'password123',
            'role': 'employer',
            'full_name': 'Employer Alice'
        }
        res = self.client.post('/api/auth/register', json=employer_reg_data)
        self.assertEqual(res.status_code, 201)
        employer_user_id = json.loads(res.data)['user']['id']

        # 5. Login verification
        login_res = self.client.post('/api/auth/login', json={
            'email': 'student@example.com',
            'password': 'password123'
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = json.loads(login_res.data)
        self.assertEqual(login_data['user']['id'], student_user_id)

        # 6. Update student profile parameters
        profile_update_res = self.client.post('/api/students/profile', json={
            'user_id': student_user_id,
            'full_name': 'Parth Student Updated',
            'institution_id': faculty_user_id,
            'current_track': 'Backend Development',
            'digital_wallet_address': '0xABC123XYZ'
        })
        self.assertEqual(profile_update_res.status_code, 200)
        profile_data = json.loads(profile_update_res.data)['profile']
        self.assertEqual(profile_data['full_name'], 'Parth Student Updated')
        self.assertEqual(profile_data['institution_id'], faculty_user_id)
        self.assertEqual(profile_data['current_track'], 'Backend Development')
        self.assertEqual(profile_data['digital_wallet_address'], '0xABC123XYZ')

        # 7. Add Learning Nodes (Curriculum engine)
        node_sql_res = self.client.post('/api/students/learning_nodes', json={
            'title': 'Introduction to SQL',
            'track_name': 'Backend Development'
        })
        self.assertEqual(node_sql_res.status_code, 201)
        node_sql_id = json.loads(node_sql_res.data)['node']['id']

        node_flask_res = self.client.post('/api/students/learning_nodes', json={
            'title': 'Flask REST APIs',
            'track_name': 'Backend Development',
            'prerequisites': [node_sql_id]
        })
        self.assertEqual(node_flask_res.status_code, 201)
        node_flask_id = json.loads(node_flask_res.data)['node']['id']

        # Check node list endpoint
        nodes_get_res = self.client.get('/api/students/learning_nodes?track_name=Backend+Development')
        self.assertEqual(nodes_get_res.status_code, 200)
        self.assertEqual(len(json.loads(nodes_get_res.data)), 2)

        # 8. Start and complete Node A (SQL)
        progress_res = self.client.post('/api/students/progress', json={
            'student_id': student_user_id,
            'node_id': node_sql_id,
            'status': 'ACTIVE',
            'score': 10
        })
        self.assertEqual(progress_res.status_code, 200)
        
        progress_res = self.client.post('/api/students/progress', json={
            'student_id': student_user_id,
            'node_id': node_sql_id,
            'status': 'COMPLETED',
            'score': 95
        })
        self.assertEqual(progress_res.status_code, 200)
        self.assertEqual(json.loads(progress_res.data)['progress']['status'], 'COMPLETED')

        # Start Node B (Flask)
        progress_res = self.client.post('/api/students/progress', json={
            'student_id': student_user_id,
            'node_id': node_flask_id,
            'status': 'ACTIVE'
        })
        self.assertEqual(progress_res.status_code, 200)

        # 9. Trigger Stuck flow on Node B (Flask)
        stuck_res = self.client.post('/api/ai/stuck', json={
            'student_user_id': student_user_id,
            'node_id': node_flask_id,
            'query_text': 'I am getting a circular import error when trying to initialize SQLAlchemy.'
        })
        self.assertEqual(stuck_res.status_code, 200)
        stuck_data = json.loads(stuck_res.data)
        self.assertIn("tasks", stuck_data['intervention']['generated_micro_tasks'])
        self.assertEqual(stuck_data['intervention']['resolution_status'], 'PENDING')
        intervention_id = stuck_data['intervention']['id']

        # Verify node progress status changed to STUCK
        progress_check_res = self.client.get(f'/api/students/progress/{student_user_id}')
        self.assertEqual(progress_check_res.status_code, 200)
        progress_records = json.loads(progress_check_res.data)
        flask_progress = next(p for p in progress_records if p['node_id'] == node_flask_id)
        self.assertEqual(flask_progress['status'], 'STUCK')

        # 10. Mentor claims intervention
        claim_res = self.client.post(f'/api/mentor/interventions/{intervention_id}/assign', json={
            'mentor_user_id': mentor_user_id
        })
        self.assertEqual(claim_res.status_code, 200)
        claim_data = json.loads(claim_res.data)
        self.assertEqual(claim_data['intervention']['resolution_status'], 'REVIEWING')
        self.assertEqual(claim_data['intervention']['assigned_mentor_id'], mentor_user_id)

        # 11. Mentor resolves intervention and marks student progress as COMPLETED
        resolve_res = self.client.post(f'/api/mentor/interventions/{intervention_id}/resolve', json={
            'mentor_user_id': mentor_user_id,
            'next_status': 'COMPLETED'
        })
        self.assertEqual(resolve_res.status_code, 200)
        resolve_data = json.loads(resolve_res.data)
        self.assertEqual(resolve_data['intervention']['resolution_status'], 'RESOLVED')
        self.assertEqual(resolve_data['student_progress']['status'], 'COMPLETED')

        # 12. Create Employer Micro-Apprenticeships
        # Apprenticeship matching completed Node A (SQL)
        job_match_res = self.client.post('/api/employer/apprenticeships', json={
            'employer_id': employer_user_id,
            'required_skill_node_id': node_sql_id,
            'task_title': 'SQL Query Optimization Specialist',
            'stipend_amount': 250
        })
        self.assertEqual(job_match_res.status_code, 201)
        job_match_id = json.loads(job_match_res.data)['apprenticeship']['id']

        # Apprenticeship requiring another node (not completed by student)
        node_another_res = self.client.post('/api/students/learning_nodes', json={
            'title': 'Advanced Kubernetes Orchestration',
            'track_name': 'DevOps'
        })
        node_another_id = json.loads(node_another_res.data)['node']['id']

        job_no_match_res = self.client.post('/api/employer/apprenticeships', json={
            'employer_id': employer_user_id,
            'required_skill_node_id': node_another_id,
            'task_title': 'Kubernetes Deployer',
            'stipend_amount': 500
        })
        self.assertEqual(job_no_match_res.status_code, 201)

        # 13. Query student dashboard and verify matching
        dash_res = self.client.get(f'/api/students/dashboard/{student_user_id}')
        self.assertEqual(dash_res.status_code, 200)
        dash_data = json.loads(dash_res.data)
        
        # Verify student details
        self.assertEqual(dash_data['student_profile']['full_name'], 'Parth Student Updated')
        
        # Verify matched apprenticeships only contains the one for SQL, not Kubernetes
        self.assertEqual(len(dash_data['matched_apprenticeships']), 1)
        self.assertEqual(dash_data['matched_apprenticeships'][0]['task_title'], 'SQL Query Optimization Specialist')
        self.assertEqual(dash_data['matched_apprenticeships'][0]['stipend_amount'], 250)

        # Verify matched apprenticeships via direct GET endpoint
        matched_get_res = self.client.get(f'/api/employer/apprenticeships/matched/{student_user_id}')
        self.assertEqual(matched_get_res.status_code, 200)
        matched_get_data = json.loads(matched_get_res.data)
        self.assertEqual(len(matched_get_data), 1)
        self.assertEqual(matched_get_data[0]['id'], job_match_id)

        # 14. Update apprenticeship status
        status_update_res = self.client.post(f'/api/employer/apprenticeships/{job_match_id}/status', json={
            'status': 'IN_PROGRESS'
        })
        self.assertEqual(status_update_res.status_code, 200)
        self.assertEqual(json.loads(status_update_res.data)['apprenticeship']['status'], 'IN_PROGRESS')

        # Verify it no longer appears in matched list since status is not OPEN anymore
        matched_get_res2 = self.client.get(f'/api/employer/apprenticeships/matched/{student_user_id}')
        self.assertEqual(matched_get_res2.status_code, 200)
        self.assertEqual(len(json.loads(matched_get_res2.data)), 0)

if __name__ == '__main__':
    unittest.main()
