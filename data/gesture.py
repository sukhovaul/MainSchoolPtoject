import sqlalchemy as sa
from .db_session import SqlAlchemyBase

class Gesture(SqlAlchemyBase):
    __tablename__ = 'gestures'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    word = sa.Column(sa.String, nullable=False)
    video_filename = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.Text, nullable=True)