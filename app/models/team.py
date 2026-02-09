from app.extensions import db


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organizations.id"), nullable=False
    )
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.id"), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey("leagues.id"), nullable=False)
    abbrev = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    source_team_id = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("organization_id", "season_id", name="uq_org_season"),
    )

    organization = db.relationship("Organization", back_populates="teams")
    season = db.relationship("Season", back_populates="teams")
    league = db.relationship("League", back_populates="teams")
    players = db.relationship("Player", back_populates="team_rel", lazy="dynamic")
    home_games = db.relationship(
        "Game",
        foreign_keys="Game.home_team_id",
        back_populates="home_team",
        lazy="dynamic",
    )
    away_games = db.relationship(
        "Game",
        foreign_keys="Game.away_team_id",
        back_populates="away_team",
        lazy="dynamic",
    )
    team_stats = db.relationship("TeamStats", back_populates="team", lazy="dynamic")

    def __repr__(self):
        return f"<Team {self.name}>"
