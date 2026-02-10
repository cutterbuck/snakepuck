from app.extensions import db


class PlayerStats(db.Model):
    __tablename__ = "player_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=False
    )
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)

    games_played = db.Column(db.Integer, nullable=False, default=0)
    goals = db.Column(db.Integer, nullable=False, default=0)
    assists = db.Column(db.Integer, nullable=False, default=0)
    points = db.Column(db.Integer, nullable=False, default=0)
    shots = db.Column(db.Integer, nullable=False, default=0)
    shooting_pct = db.Column(db.Float, nullable=True)
    faceoffs_won = db.Column(db.Integer, nullable=False, default=0)
    faceoffs_lost = db.Column(db.Integer, nullable=False, default=0)
    faceoff_pct = db.Column(db.Float, nullable=True)
    penalties = db.Column(db.Integer, nullable=False, default=0)
    penalties_drawn = db.Column(db.Integer, nullable=False, default=0)
    blocks = db.Column(db.Integer, nullable=False, default=0)
    checks = db.Column(db.Integer, nullable=False, default=0)
    xg = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (
        db.UniqueConstraint("player_id", "season_id", name="uq_player_season_stats"),
    )

    player = db.relationship("Player", back_populates="player_stats")
    season = db.relationship("Season", back_populates="player_stats")

    def __repr__(self):
        return f"<PlayerStats player={self.player_id} season_id={self.season_id}>"
