from app.extensions import db


class Stint(db.Model):
    __tablename__ = "stints"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey("games.game_id"), nullable=False)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=False
    )
    period = db.Column(db.Integer, nullable=True)
    period_time_start = db.Column(db.Float, nullable=True)
    period_time_end = db.Column(db.Float, nullable=True)
    game_stint = db.Column(db.Integer, nullable=True)
    n_home_skaters = db.Column(db.Integer, nullable=True)
    n_away_skaters = db.Column(db.Integer, nullable=True)
    is_home_net_empty = db.Column(db.Boolean, nullable=True)
    is_away_net_empty = db.Column(db.Boolean, nullable=True)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    source_team_id = db.Column(db.String(36), nullable=True)
    team_abbr = db.Column(db.String(10), nullable=True)
    shift = db.Column(db.Integer, nullable=True)
    i_xg = db.Column(db.Float, nullable=True)
    oi_xgf = db.Column(db.Float, nullable=True)
    oi_xga = db.Column(db.Float, nullable=True)

    game = db.relationship("Game", back_populates="stints")
    player = db.relationship("Player", back_populates="stints")

    def __repr__(self):
        return f"<Stint game={self.game_id} player={self.player_id} stint={self.game_stint}>"
