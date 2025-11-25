import sqlalchemy as sa
from sqlalchemy import ForeignKey
from .db_session import SqlAlchemyBase

class Module(SqlAlchemyBase):
    __tablename__ = 'modules'

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True) #id модуля
    title = sa.Column(sa.String, nullable=False) #название
    description = sa.Column(sa.Text, nullable=True) #описание
    order_index = sa.Column(sa.Integer, nullable=False) #номер по порядку на сайте