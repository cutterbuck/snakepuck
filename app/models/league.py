from app.extensions import db


class League(db.Model):
    __tablename__ = "leagues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    abbrev = db.Column(db.String(10), unique=True, nullable=False)

    teams = db.relationship("Team", back_populates="league", lazy="dynamic")
    games = db.relationship("Game", back_populates="league", lazy="dynamic")

    def __repr__(self):
        return f"<League {self.abbrev}>"
