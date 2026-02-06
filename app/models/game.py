from app.extensions import db


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    home_team_score = db.Column(db.Integer, nullable=False)
    away_team_score = db.Column(db.Integer, nullable=False)
    last_period = db.Column(db.Integer, nullable=True)
    source_game_id = db.Column(db.Integer, nullable=True)

    home_team = db.relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_games"
    )
    away_team = db.relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_games"
    )

    def __repr__(self):
        return f"<Game {self.date} {self.home_team_id} vs {self.away_team_id}>"
