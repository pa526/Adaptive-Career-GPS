# Adaptive Career GPS

## Project Overview

The Adaptive Career GPS is a dynamic and intelligent platform designed to guide students through their career development journey, connect them with mentors and employers, and provide AI-driven interventions when they encounter learning obstacles. The system facilitates personalized learning paths, tracks student progress, and matches students with relevant micro-apprenticeships based on their acquired skills.

## Features

-   **User Authentication & Role Management**: Secure registration and login for Students, Mentors, Faculty, and Employers.
-   **Student Profile Management**: Students can update their profiles, track learning progress, and view personalized dashboards.
-   **Learning Node Tracking**: Defines and tracks progress through a curriculum of learning nodes, including prerequisites and status (LOCKED, ACTIVE, STUCK, COMPLETED).
-   **AI-Powered Interventions**: When students get 'stuck' on a learning node, the system leverages the Gemini API to generate micro-tasks and identify learning gaps, providing targeted support.
-   **Mentor Support System**: Mentors can claim and resolve student interventions, guiding them through challenges and helping them progress.
-   **Employer Micro-Apprenticeships**: Employers can post micro-apprenticeship opportunities linked to specific learning nodes, offering practical experience and stipends.
-   **Intelligent Matching**: Students are matched with relevant micro-apprenticeships based on their completed learning nodes and current progress.

## Architecture

The Adaptive Career GPS is built as a Flask-based RESTful API backend, utilizing SQLAlchemy for database interactions. The application follows a modular structure with blueprints for different functionalities (student, mentor, AI, employer routes).

-   **Backend Framework**: Flask
-   **Database**: SQLAlchemy (ORM) with SQLite (default) or other compatible databases.
-   **AI Integration**: Google Gemini API via `langchain` and `langchain-google-genai` for intelligent interventions.
-   **CORS**: Flask-CORS for handling Cross-Origin Resource Sharing.
-   **Authentication**: `werkzeug.security` for password hashing.

## Setup and Installation

To set up the Adaptive Career GPS project locally, follow these steps:

### Prerequisites

-   Python 3.8+
-   `pip` (Python package installer)
-   A Google Gemini API Key (optional, but recommended for full AI functionality)

### 1. Clone the Repository

```bash
git clone https://github.com/pa526/Adaptive-Career-GPS.git
cd Adaptive-Career-GPS
```

### 2. Create a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

Install the required Python packages:

```bash
pip install -r career_gps_mvp/requirements.txt
```

### 4. Configuration

Create a `.env` file in the `career_gps_mvp` directory (e.g., `career_gps_mvp/.env`) and add your configuration. A `SECRET_KEY` is essential for security, and a `GEMINI_API_KEY` is needed for AI features.

```ini
SECRET_KEY="your_super_secret_key_here"
DATABASE_URL="sqlite:///career_gps.db" # Optional: specify a different database URL
GEMINI_API_KEY="your_gemini_api_key_here" # Required for AI interventions
```

If `GEMINI_API_KEY` is not provided, the AI routes will operate in a mock mode, returning predefined responses.

### 5. Run the Application

Navigate to the `career_gps_mvp` directory and run the Flask application:

```bash
cd career_gps_mvp
python app.py
```

The application will start on `http://127.0.0.1:5000` (or `http://localhost:5000`).

## API Endpoints

The API provides various endpoints for different user roles and functionalities. Below is a summary of key endpoints:

### Authentication

-   `POST /api/auth/register`: Register a new user (Student, Mentor, Faculty, Employer).
-   `POST /api/auth/login`: Authenticate a user and receive user details.

### Student Endpoints

-   `GET /api/students/profile/<user_id>`: Retrieve a student's profile.
-   `POST /api/students/profile`: Update a student's profile.
-   `GET /api/students/dashboard/<user_id>`: Get a comprehensive dashboard for a student, including progress, interventions, and matched apprenticeships.
-   `POST /api/students/progress`: Update a student's progress on a learning node.
-   `GET /api/students/progress/<user_id>`: Get all progress records for a student.
-   `POST /api/students/learning_nodes`: Create a new learning node (primarily for setup/admin).
-   `GET /api/students/learning_nodes`: List learning nodes, with optional filtering by `track_name`.

### Mentor Endpoints

-   `GET /api/mentor/profile/<user_id>`: Retrieve a mentor's profile.
-   `POST /api/mentor/profile`: Update a mentor's profile.
-   `GET /api/mentor/interventions`: List AI interventions, with filtering options.
-   `POST /api/mentor/interventions/<intervention_id>/assign`: Assign an intervention to a mentor.
-   `POST /api/mentor/interventions/<intervention_id>/resolve`: Resolve an intervention, updating student progress.

### AI Endpoints

-   `POST /api/ai/stuck`: Trigger an AI intervention for a student stuck on a learning node.
-   `GET /api/ai/interventions/<user_id>`: Get a student's intervention history.

### Employer Endpoints

-   `POST /api/employer/apprenticeships`: Create a new micro-apprenticeship opportunity.
-   `GET /api/employer/apprenticeships`: List micro-apprenticeships, with filtering options.
-   `POST /api/employer/apprenticeships/<apprenticeship_id>/status`: Update the status of a micro-apprenticeship.
-   `GET /api/employer/apprenticeships/matched/<student_user_id>`: Get micro-apprenticeships matched to a specific student.

## Contributing

We welcome contributions to the Adaptive Career GPS! Please feel free to fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the LICENSE file for details. (Note: A `LICENSE` file is assumed to exist or should be created.)
