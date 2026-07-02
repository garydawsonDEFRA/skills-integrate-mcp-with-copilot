"""
High School Management System API

A FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.

This version uses persistent SQLite database storage.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, Column, String, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
import os
from pathlib import Path

# Database setup
DATABASE_URL = "sqlite:///./mergington_activities.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class Activity(Base):
    """Activity model for storing extracurricular activities"""
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    schedule = Column(String)
    max_participants = Column(Integer)
    
    # Relationship to enrollments
    enrollments = relationship("Enrollment", back_populates="activity", cascade="all, delete-orphan")


class Enrollment(Base):
    """Enrollment model for storing student signups"""
    __tablename__ = "enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"))
    student_email = Column(String, index=True)
    
    # Relationship back to activity
    activity = relationship("Activity", back_populates="enrollments")


# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


def init_database():
    """Initialize the database with seed data if empty"""
    db = SessionLocal()
    try:
        # Check if database already has activities
        existing_count = db.query(Activity).count()
        if existing_count == 0:
            # Seed data
            activities_data = [
                {
                    "name": "Chess Club",
                    "description": "Learn strategies and compete in chess tournaments",
                    "schedule": "Fridays, 3:30 PM - 5:00 PM",
                    "max_participants": 12,
                    "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
                },
                {
                    "name": "Programming Class",
                    "description": "Learn programming fundamentals and build software projects",
                    "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
                    "max_participants": 20,
                    "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
                },
                {
                    "name": "Gym Class",
                    "description": "Physical education and sports activities",
                    "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
                    "max_participants": 30,
                    "participants": ["john@mergington.edu", "olivia@mergington.edu"]
                },
                {
                    "name": "Soccer Team",
                    "description": "Join the school soccer team and compete in matches",
                    "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
                    "max_participants": 22,
                    "participants": ["liam@mergington.edu", "noah@mergington.edu"]
                },
                {
                    "name": "Basketball Team",
                    "description": "Practice and play basketball with the school team",
                    "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
                    "max_participants": 15,
                    "participants": ["ava@mergington.edu", "mia@mergington.edu"]
                },
                {
                    "name": "Art Club",
                    "description": "Explore your creativity through painting and drawing",
                    "schedule": "Thursdays, 3:30 PM - 5:00 PM",
                    "max_participants": 15,
                    "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
                },
                {
                    "name": "Drama Club",
                    "description": "Act, direct, and produce plays and performances",
                    "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
                    "max_participants": 20,
                    "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
                },
                {
                    "name": "Math Club",
                    "description": "Solve challenging problems and participate in math competitions",
                    "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
                    "max_participants": 10,
                    "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
                },
                {
                    "name": "Debate Team",
                    "description": "Develop public speaking and argumentation skills",
                    "schedule": "Fridays, 4:00 PM - 5:30 PM",
                    "max_participants": 12,
                    "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
                }
            ]
            
            # Create activities and enrollments
            for activity_data in activities_data:
                participants = activity_data.pop("participants")
                activity = Activity(**activity_data)
                db.add(activity)
                db.flush()  # Flush to get the activity ID
                
                # Add enrollments
                for email in participants:
                    enrollment = Enrollment(activity_id=activity.id, student_email=email)
                    db.add(enrollment)
            
            db.commit()
    finally:
        db.close()


def format_activities_response(db: Session):
    """Format activities from database into the response format expected by frontend"""
    activities_dict = {}
    activities = db.query(Activity).all()
    
    for activity in activities:
        participants = [e.student_email for e in activity.enrollments]
        activities_dict[activity.name] = {
            "description": activity.description,
            "schedule": activity.schedule,
            "max_participants": activity.max_participants,
            "participants": participants
        }
    
    return activities_dict


@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup"""
    init_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    """Get all activities with their participants"""
    db = SessionLocal()
    try:
        return format_activities_response(db)
    finally:
        db.close()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    db = SessionLocal()
    try:
        # Validate activity exists
        activity = db.query(Activity).filter(Activity.name == activity_name).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Validate student is not already signed up
        existing_enrollment = db.query(Enrollment).filter(
            Enrollment.activity_id == activity.id,
            Enrollment.student_email == email
        ).first()
        
        if existing_enrollment:
            raise HTTPException(
                status_code=400,
                detail="Student is already signed up"
            )
        
        # Add enrollment
        enrollment = Enrollment(activity_id=activity.id, student_email=email)
        db.add(enrollment)
        db.commit()
        
        return {"message": f"Signed up {email} for {activity_name}"}
    finally:
        db.close()


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    db = SessionLocal()
    try:
        # Validate activity exists
        activity = db.query(Activity).filter(Activity.name == activity_name).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        
        # Validate student is signed up
        enrollment = db.query(Enrollment).filter(
            Enrollment.activity_id == activity.id,
            Enrollment.student_email == email
        ).first()
        
        if not enrollment:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity"
            )
        
        # Remove enrollment
        db.delete(enrollment)
        db.commit()
        
        return {"message": f"Unregistered {email} from {activity_name}"}
    finally:
        db.close()
