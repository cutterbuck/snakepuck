from app.extensions import db


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    playerId = db.Column(db.String(36), unique=True, nullable=True)
    firstName = db.Column(db.String(80), nullable=False)
    lastName = db.Column(db.String(80), nullable=False)
    nationality = db.Column(db.String(10), nullable=True)
    birthDate = db.Column(db.Date, nullable=True)
    birthPlace = db.Column(db.Date, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Integer, nullable=True)
    position = db.Column(db.String(5), nullable=True)
    position_group = db.Column(db.String(5), nullable=True)
    handed = db.Column(db.String(5), nullable=True)
    shootsCatches = db.Column(db.String(5), nullable=True)

    stints = db.relationship("Stint", back_populates="player", lazy="dynamic")
    events = db.relationship("Event", back_populates="player", lazy="dynamic")
    tracking_data = db.relationship("Tracking", back_populates="player", lazy="dynamic")
    player_stats = db.relationship(
        "PlayerStats", back_populates="player", lazy="dynamic"
    )
    player_game_stats = db.relationship(
        "PlayerGameStats", back_populates="player", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Player {self.firstName} {self.lastName}>"
