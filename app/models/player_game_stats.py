from app.extensions import db


class PlayerGameStats(db.Model):
    __tablename__ = "player_game_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=False, index=True
    )
    game_id = db.Column(
        db.String(36), db.ForeignKey("games.game_id"), nullable=False, index=True
    )
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)

    tot_goals = db.Column(db.Integer, nullable=False, default=0)
    tot_assists = db.Column(db.Integer, nullable=False, default=0)
    tot_points = db.Column(db.Integer, nullable=False, default=0)
    es_goals = db.Column(db.Integer, nullable=False, default=0)
    es_assists = db.Column(db.Integer, nullable=False, default=0)
    es_points = db.Column(db.Integer, nullable=False, default=0)
    ev5_goals = db.Column(db.Integer, nullable=False, default=0)
    ev5_assists = db.Column(db.Integer, nullable=False, default=0)
    ev5_points = db.Column(db.Integer, nullable=False, default=0)
    pp_goals = db.Column(db.Integer, nullable=False, default=0)
    pp_assists = db.Column(db.Integer, nullable=False, default=0)
    pp_points = db.Column(db.Integer, nullable=False, default=0)
    pk_goals = db.Column(db.Integer, nullable=False, default=0)
    pk_assists = db.Column(db.Integer, nullable=False, default=0)
    pk_points = db.Column(db.Integer, nullable=False, default=0)
    shots = db.Column(db.Integer, nullable=False, default=0)
    shooting_pct = db.Column(db.Float, nullable=True)
    faceoffs_won = db.Column(db.Integer, nullable=False, default=0)
    faceoffs_lost = db.Column(db.Integer, nullable=False, default=0)
    faceoff_pct = db.Column(db.Float, nullable=True)
    penalties = db.Column(db.Integer, nullable=False, default=0)
    penalties_drawn = db.Column(db.Integer, nullable=False, default=0)
    blocks = db.Column(db.Integer, nullable=False, default=0)
    checks = db.Column(db.Integer, nullable=False, default=0)
    tot_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    tot_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    tot_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    es_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    es_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    es_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    ev5_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    ev5_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    ev5_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    pp_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    pp_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    pp_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    pk_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    pk_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    pk_oi_xga = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (
        db.UniqueConstraint(
            "player_id", "game_id", "team_id", name="uq_player_game_team_stats"
        ),
    )

    player = db.relationship("Player", back_populates="player_game_stats")
    game = db.relationship("Game", back_populates="player_game_stats")
    team = db.relationship("Team")
    season = db.relationship("Season")

    def __repr__(self):
        return f"<PlayerGameStats player={self.player_id} game={self.game_id}>"
