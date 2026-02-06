from app.extensions import db


class Season(db.Model):
    __tablename__ = "seasons"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    league = db.Column(db.String(50), nullable=True)

    teams = db.relationship("Team", back_populates="season", lazy="dynamic")

    def __repr__(self):
        return f"<Season {self.name}>"
