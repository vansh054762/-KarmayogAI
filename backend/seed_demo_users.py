"""
Seed demo users for testing KarmayogAI.
Run: python seed_demo_users.py
"""
from app import create_app
from models.database import db, User
from utils.passwords import hash_password

app = create_app()

with app.app_context():
    demo_users = [
        {
            'name': 'Admin User',
            'email': 'admin@karmayogai.gov.in',
            'password': 'Admin@123',
            'role': 'admin',
            'department': 'Ministry of Statistics & PI',
            'designation': 'Platform Administrator'
        },
        {
            'name': 'Employee User',
            'email': 'employee@karmayogai.gov.in',
            'password': 'Employee@123',
            'role': 'employee',
            'department': 'Ministry of Finance',
            'designation': 'Statistical Officer'
        },
        {
            'name': 'Priya Sharma',
            'email': 'priya@karmayogai.gov.in',
            'password': 'Employee@123',
            'role': 'employee',
            'department': 'NITI Aayog',
            'designation': 'Data Analyst'
        }
    ]

    for ud in demo_users:
        existing = User.query.filter_by(email=ud['email']).first()
        if not existing:
            user = User(
                name=ud['name'],
                email=ud['email'],
                password_hash=hash_password(ud['password']),
                role=ud['role'],
                department=ud['department'],
                designation=ud['designation']
            )
            db.session.add(user)
            print(f"✅ Created: {ud['email']}")
        else:
            print(f"⏭️  Skipped (already exists): {ud['email']}")

    db.session.commit()
    print("\n✅ Demo users ready!")
