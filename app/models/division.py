from app.extensions import db


class Division(db.Model):
    __tablename__ = "divisions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("name", "league_id", name="uq_division_league"),
    )

    league = db.relationship("League", back_populates="divisions")
    team_stats = db.relationship("TeamStats", back_populates="division", lazy="dynamic")

    def __repr__(self):
        return f"<Division {self.name}>"
