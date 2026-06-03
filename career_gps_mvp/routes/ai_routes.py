import json
from flask import Blueprint, request, jsonify, current_app
from career_gps_mvp.models.database import (
    db, StudentProfile, LearningNode, StudentNodeProgress, NodeStatus,
    AIIntervention, InterventionStatus
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ai/stuck', methods=['POST'])
def get_ai_help():
    """Trigger the 'I'm Stuck' LangChain + Gemini workflow to generate structured interventions."""
    data = request.get_json() or {}
    student_user_id = data.get('student_user_id')
    node_id = data.get('node_id')
    query_text = data.get('query_text')  # Optional text from the student describing why they are stuck

    if not student_user_id or not node_id:
        return jsonify({'error': 'Missing required fields: student_user_id, node_id'}), 400

    # Verify student exists
    student = StudentProfile.query.filter_by(user_id=student_user_id).first()
    if not student:
        return jsonify({'error': 'Student profile not found'}), 404

    # Verify learning node exists
    node = LearningNode.query.filter_by(id=node_id).first()
    if not node:
        return jsonify({'error': 'Learning node not found'}), 404

    # Fetch or create the progress record
    progress = StudentNodeProgress.query.filter_by(student_id=student_user_id, node_id=node_id).first()
    if not progress:
        progress = StudentNodeProgress(
            student_id=student_user_id,
            node_id=node_id,
            status=NodeStatus.STUCK,
            stagnation_days=1,
            score=0
        )
        db.session.add(progress)
    else:
        progress.status = NodeStatus.STUCK
        progress.stagnation_days = (progress.stagnation_days or 0) + 1

    api_key = current_app.config.get('GEMINI_API_KEY')
    identified_gap = ""
    generated_tasks = {}

    if not api_key:
        # Fallback Mock JSON response
        current_app.logger.warning("GEMINI_API_KEY is empty. Using structured mock AI response.")
        identified_gap = f"The student is stuck on learning node '{node.title}' in the track '{node.track_name}'. They reported: '{query_text or 'No details provided'}'."
        generated_tasks = {
            "tasks": [
                {
                    "title": f"Review Core Concepts of {node.title}",
                    "description": "Read introductory guides and write down 3 key concepts."
                },
                {
                    "title": "Build a Simple Sandbox project",
                    "description": "Write a 50-line code snippet demonstrating the node's practical application."
                },
                {
                    "title": "Prepare Mentor Discussion Points",
                    "description": "Write down a specific question highlighting where execution breaks down."
                }
            ]
        }
    else:
        try:
            # Initialize ChatGoogleGenerativeAI model
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.7
            )

            # Design prompt template that forces structured JSON output
            prompt = ChatPromptTemplate.from_messages([
                ("system", (
                    "You are a professional Career Coach and Mentor on the Adaptive Career GPS platform.\n"
                    "Identify the learning gap based on the node details and query, and suggest exactly 3 micro-tasks.\n"
                    "You MUST respond ONLY with a raw JSON object. Do not include markdown wrappers like ```json or similar.\n"
                    "Response JSON structure must be:\n"
                    "{\n"
                    "  \"identified_gap\": \"A detailed explanation of the conceptual gap the student is experiencing\",\n"
                    "  \"tasks\": [\n"
                    "    {\"title\": \"Task 1 Title\", \"description\": \"Task 1 Description\"},\n"
                    "    {\"title\": \"Task 2 Title\", \"description\": \"Task 2 Description\"},\n"
                    "    {\"title\": \"Task 3 Title\", \"description\": \"Task 3 Description\"}\n"
                    "  ]\n"
                    "}"
                )),
                ("user", (
                    "Student Track: {track_name}\n"
                    "Stuck Learning Node: {node_title}\n"
                    "Student Description of Block: {query}\n\n"
                    "Provide your structured gap analysis and 3-step action plan:"
                ))
            ])

            # Setup chain
            chain = prompt | llm | StrOutputParser()

            # Execute chain
            raw_response = chain.invoke({
                "track_name": node.track_name,
                "node_title": node.title,
                "query": query_text or "No detailed description provided."
            })

            # Clean and parse JSON response
            clean_text = raw_response.strip()
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()

            parsed = json.loads(clean_text)
            identified_gap = parsed.get("identified_gap", f"Student is struggling with {node.title}.")
            generated_tasks = {"tasks": parsed.get("tasks", [])}

        except Exception as e:
            current_app.logger.error(f"LangChain/Gemini execution error: {str(e)}")
            identified_gap = f"Failed to call AI: {str(e)}. Fallback to manual review for {node.title}."
            generated_tasks = {
                "tasks": [
                    {
                        "title": "Request Mentor Review",
                        "description": "Connect with an assigned mentor to diagnose why you are stuck on this node."
                    }
                ]
            }

    # Save the session/intervention to database
    intervention = AIIntervention(
        progress_id=progress.id,
        identified_gap=identified_gap,
        generated_micro_tasks=generated_tasks,
        resolution_status=InterventionStatus.PENDING
    )

    try:
        db.session.add(intervention)
        db.session.commit()
        return jsonify({
            'message': 'AI intervention generated successfully and student status set to STUCK.',
            'intervention': intervention.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error saving AI Intervention: {str(e)}'}), 500


@ai_bp.route('/api/ai/interventions/student/<string:student_id>', methods=['GET'])
def get_student_interventions(student_id):
    """Retrieve history of AI interventions for a student."""
    interventions = AIIntervention.query.join(StudentNodeProgress).filter(
        StudentNodeProgress.student_id == student_id
    ).order_by(StudentNodeProgress.id.desc()).all()
    
    return jsonify([i.to_dict() for i in interventions]), 200
