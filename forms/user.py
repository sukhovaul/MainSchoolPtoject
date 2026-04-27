from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed # Добавляем эти импорты
from wtforms import StringField, PasswordField, TextAreaField, SubmitField, EmailField
from wtforms.validators import DataRequired

class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired()])
    name = StringField('Имя пользователя', validators=[DataRequired()])
    
    # Поле TextArea, куда попадет текст
    about = TextAreaField("Немного о себе")
    
    # Новое поле для выбора файла
    about_file = FileField('Загрузить из .txt', validators=[
        FileAllowed(['txt'], 'Разрешены только текстовые файлы!')
    ])
    
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')