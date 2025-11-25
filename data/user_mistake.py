import sqlalchemy as sa
from sqlalchemy import ForeignKey
from .db_session import SqlAlchemyBase

class UserMistake(SqlAlchemyBase):
    __tablename__ = 'user_mistakes'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, ForeignKey('users.id'), nullable=False)
    gesture_id = sa.Column(sa.Integer, ForeignKey('gestures.id'), nullable=False)
    lesson_id = sa.Column(sa.Integer, ForeignKey('lessons.id'), nullable=True)
    module_id = sa.Column(sa.Integer, ForeignKey('modules.id'), nullable=True)
    incorrect_answer = sa.Column(sa.String, nullable=True)
    mistake_count = sa.Column(sa.Integer, default=1)