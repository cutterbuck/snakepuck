from app.extensions import db


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    abbreviation = db.Column(db.String(10), nullable=True)

    teams = db.relationship("Team", back_populates="organization", lazy="dynamic")

    def __repr__(self):
        return f"<Organization {self.name}>"
