import sqlalchemy as sa
from sqlalchemy import ForeignKey
from .db_session import SqlAlchemyBase

class LessonGesture(SqlAlchemyBase):
    __tablename__ = 'lesson_gestures'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    lesson_id = sa.Column(sa.Integer, ForeignKey('lessons.id'), nullable=False)
    gesture_id = sa.Column(sa.Integer, ForeignKey('gestures.id'), nullable=False)
    order_index = sa.Column(sa.Integer, nullable=False)