from app.extensions import db


class Tracking(db.Model):
    __tablename__ = "tracking"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(
        db.String(36), db.ForeignKey("games.game_id"), nullable=False, index=True
    )
    sl_event_id = db.Column(db.String(36), nullable=True, index=True)
    team_id = db.Column(db.String(36), nullable=True)
    team_name = db.Column(db.String(120), nullable=True)
    player_id = db.Column(
        db.String(36), db.ForeignKey("players.playerId"), nullable=True, index=True
    )
    player_name = db.Column(db.String(160), nullable=True)
    tracking_x = db.Column(db.Float, nullable=True)
    tracking_y = db.Column(db.Float, nullable=True)
    tracking_vel_x = db.Column(db.Float, nullable=True)
    tracking_vel_y = db.Column(db.Float, nullable=True)

    game = db.relationship("Game", back_populates="tracking_data")
    player = db.relationship("Player", back_populates="tracking_data")

    def __repr__(self):
        return f"<Tracking game={self.game_id} player={self.player_id} event={self.sl_event_id}>"
