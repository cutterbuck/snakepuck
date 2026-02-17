from app.extensions import db


class PlayerStats(db.Model):
    __tablename__ = "player_stats"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=False
    )
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)

    games_played = db.Column(db.Integer, nullable=False, default=0)
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
    tot_xg_pct = db.Column(db.Float, nullable=True)
    es_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    es_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    es_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    es_xg_pct = db.Column(db.Float, nullable=True)
    ev5_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    ev5_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    ev5_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    ev5_xg_pct = db.Column(db.Float, nullable=True)
    pp_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    pp_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    pp_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    pp_xg_pct = db.Column(db.Float, nullable=True)
    pk_i_xg = db.Column(db.Float, nullable=False, default=0.0)
    pk_oi_xgf = db.Column(db.Float, nullable=False, default=0.0)
    pk_oi_xga = db.Column(db.Float, nullable=False, default=0.0)
    pk_xg_pct = db.Column(db.Float, nullable=True)
    age = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "player_id", "season_id", "team_id", name="uq_player_season_team_stats"
        ),
    )

    player = db.relationship("Player", back_populates="player_stats")
    season = db.relationship("Season", back_populates="player_stats")
    team = db.relationship("Team", back_populates="player_stats")

    def __repr__(self):
        return f"<PlayerStats player={self.player_id} team_id={self.team_id} season_id={self.season_id}>"
