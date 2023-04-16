from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    prompt = db.Column(db.String(500), nullable=False)
    prompt_category = db.Column(db.Text, nullable=True)
