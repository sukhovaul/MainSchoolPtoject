import sqlalchemy as sa
from sqlalchemy import ForeignKey
from .db_session import SqlAlchemyBase

class Lesson(SqlAlchemyBase):
    __tablename__ = 'lessons'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True) #id урока
    module_id = sa.Column(sa.Integer, ForeignKey('modules.id'), nullable=False) #id модуля в котором тема
    title = sa.Column(sa.String, nullable=False) #название
    lesson_type = sa.Column(sa.String, nullable=False) #тип (новый материал1, новый материал2, повторение, заключение)
    order_index = sa.Column(sa.Integer, nullable=False) #порядок по номеру