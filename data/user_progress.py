import sqlalchemy as sa
from sqlalchemy import ForeignKey
from .db_session import SqlAlchemyBase

class UserProgress(SqlAlchemyBase):
    __tablename__ = 'user_progress'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    user_id = sa.Column(sa.Integer, ForeignKey('users.id'), nullable=False)
    module_id = sa.Column(sa.Integer, ForeignKey('modules.id'), nullable=False)
    correct_answers = sa.Column(sa.Integer, default=0)
    total_questions = sa.Column(sa.Integer, default=0)
    completion_percentage = sa.Column(sa.Float, default=0.0)
    is_completed = sa.Column(sa.Boolean, default=False)