from app.extensions import db


class TeamStats(db.Model):
    __tablename__ = "team_stats"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    division_id = db.Column(db.Integer, db.ForeignKey("divisions.id"), nullable=True)

    games_played = db.Column(db.Integer, nullable=False, default=0)
    wins = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    ot_losses = db.Column(db.Integer, nullable=False, default=0)
    points = db.Column(db.Integer, nullable=False, default=0)
    points_percentage = db.Column(db.Float, nullable=False, default=0.0)
    regulation_wins = db.Column(db.Integer, nullable=False, default=0)
    regulation_or_ot_wins = db.Column(db.Integer, nullable=False, default=0)
    goals_forward = db.Column(db.Integer, nullable=False, default=0)
    goals_against = db.Column(db.Integer, nullable=False, default=0)
    goal_diff = db.Column(db.Integer, nullable=False, default=0)
    so_record = db.Column(db.String(20), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("team_id", "season_id", name="uq_team_season_stats"),
    )

    team = db.relationship("Team", back_populates="team_stats")
    season = db.relationship("Season", back_populates="team_stats")
    division = db.relationship("Division", back_populates="team_stats")

    def __repr__(self):
        return f"<TeamStats team_id={self.team_id} season_id={self.season_id}>"
