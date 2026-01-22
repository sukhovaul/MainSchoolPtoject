import datetime
import sqlalchemy as sa
from .db_session import SqlAlchemyBase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
#для работы с бд как в ооп

#указываем, что это не обычный класс, а класс модели
# В классе User добавьте метод для получения прогресса
class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'
    
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username = sa.Column(sa.String, nullable=False)
    email = sa.Column(sa.String, index=True, unique=True, nullable=False)
    hashed_password = sa.Column(sa.String, nullable=True)
    about = sa.Column(sa.Text, nullable=True)
    
    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)
    
    def get_progress(self, db_sess):
        """Получает прогресс пользователя"""
        from data.user_progress import UserProgress
        return db_sess.query(UserProgress).filter(UserProgress.user_id == self.id).all()