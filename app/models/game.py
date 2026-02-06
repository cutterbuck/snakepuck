from app.extensions import db


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), unique=True, nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    home_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    away_team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    home_score = db.Column(db.Integer, nullable=False)
    away_score = db.Column(db.Integer, nullable=False)
    game_outcome = db.Column(db.String(50), nullable=True)
    home_start_net = db.Column(db.String(36), nullable=True)

    league = db.relationship("League", back_populates="games")
    home_team = db.relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_games"
    )
    away_team = db.relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_games"
    )

    def __repr__(self):
        return f"<Game {self.game_id} {self.date}>"
