import sqlalchemy
from sqlalchemy import orm
from .db_session import SqlAlchemyBase


class UserLesson(SqlAlchemyBase):
    __tablename__ = 'user_lessons'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    lesson_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('lessons.id'))
    completed_at = sqlalchemy.Column(sqlalchemy.DateTime, default=sqlalchemy.func.now())
    correct_answers = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    total_answers = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    
    user = orm.relationship('User', backref='user_lessons')
    lesson = orm.relationship('Lesson', backref='user_lessons')