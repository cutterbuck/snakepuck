from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(36), db.ForeignKey("games.game_id"), nullable=False)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=True
    )
    period = db.Column(db.Integer, nullable=True)
    period_time = db.Column(db.String(20), nullable=True)
    game_stint = db.Column(db.Integer, nullable=True)
    sl_event_id = db.Column(db.String(36), nullable=True, index=True)
    sequence_id = db.Column(db.Integer, nullable=True)
    team_abbr = db.Column(db.String(10), nullable=True)
    source_team_id = db.Column(db.String(36), nullable=True)
    opp_team_abbr = db.Column(db.String(10), nullable=True)
    opp_source_team_id = db.Column(db.String(36), nullable=True)
    event_type = db.Column(db.String(50), nullable=True)
    outcome = db.Column(db.String(50), nullable=True)
    flags = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    detail = db.Column(db.String(500), nullable=True)
    xg = db.Column(db.Float, nullable=True)
    x = db.Column(db.Float, nullable=True)
    y = db.Column(db.Float, nullable=True)
    x_adj = db.Column(db.Float, nullable=True)
    y_adj = db.Column(db.Float, nullable=True)
    has_tracking_data = db.Column(db.Boolean, nullable=True)
    event_player_tracked = db.Column(db.Boolean, nullable=True)

    game = db.relationship("Game", back_populates="events")
    player = db.relationship("Player", back_populates="events")

    def __repr__(self):
        return f"<Event {self.event_type} game={self.game_id} player={self.player_id}>"
