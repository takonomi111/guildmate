from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 中間テーブル
member_tags = db.Table('member_tags',
    db.Column('member_id', db.Integer, db.ForeignKey('member.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

member_games = db.Table('member_games',
    db.Column('member_id', db.Integer, db.ForeignKey('member.id')),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'))
)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text)
    favorite = db.Column(db.Boolean, default=False)  # ← これを追加！

    tags = db.relationship('Tag', secondary=member_tags, backref='members')
    games = db.relationship('Game', secondary=member_games, backref='members')

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    game = db.relationship('Game', backref=db.backref('events', lazy=True))
    participants = db.relationship('EventParticipant', backref='event', cascade="all, delete-orphan")

class EventParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    status = db.Column(db.String(20), default='未定')  # 参加・不参加・未定

    member = db.relationship('Member', backref='event_participations')
