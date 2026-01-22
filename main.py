from flask import Flask, render_template, redirect, request
from forms.user import RegisterForm, LoginForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from data import db_session
from flask import url_for
from data.users import User
from data.module import Module
from data.lesson import Lesson
from data.gesture import Gesture
from data.lesson_gesture import LessonGesture
from data.user_progress import UserProgress
from data.user_mistake import UserMistake


db_session.global_init("db/app.db")

app = Flask(__name__)
app.config['SECRET_KEY'] = '65432456uijhgfdsxcvbn'

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(int(user_id))

#какой URL запускает функцию
@app.route("/")
def index():
    return render_template("index.html", title = '')


@app.route('/profile')
def profile():
    return render_template('profile.html', title = '')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title = 'Регистрация', form = form, message = 'Пароли не совпадают')
        #подключаемся к бд
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            username=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        
        # Автоматический вход после регистрации
        login_user(user)
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)

@app.route('/lessons')
@login_required
def lessons():
    db_sess = db_session.create_session()
    
    # Получаем все модули
    modules = db_sess.query(Module).order_by(Module.order_index).all()
    
    # Для каждого модуля получаем уроки и прогресс
    modules_data = []
    for module in modules:
        # Получаем уроки модуля
        lessons_list = db_sess.query(Lesson).filter(
            Lesson.module_id == module.id
        ).order_by(Lesson.order_index).all()
        
        # Получаем прогресс пользователя по модулю
        user_progress = db_sess.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.module_id == module.id
        ).first()
        
        progress_percentage = user_progress.completion_percentage if user_progress else 0
        
        # Формируем данные уроков
        lessons_data = []
        for i, lesson in enumerate(lessons_list):
            # Определяем доступность урока
            # Первый урок всегда доступен, остальные - если пройден предыдущий
            available = i == 0 or (i > 0 and lessons_data[i-1]['completed'])
            completed = False  # Здесь нужно добавить логику проверки пройденных уроков
            
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'lesson_type': lesson.lesson_type,
                'available': available,
                'completed': completed
            })
        
        modules_data.append({
            'id': module.id,
            'title': module.title,
            'description': module.description,
            'progress_percentage': progress_percentage,
            'lessons': lessons_data
        })
    
    # Словари для отображения типов уроков и иконок
    lesson_types = {
        'new_gestures': 'Новые жесты',
        'repeat_new': 'Повторение новых',
        'repeat_old': 'Повторение старых',
        'final_review': 'Итоговое повторение'
    }
    
    lesson_icons = {
        'new_gestures': 'star',
        'repeat_new': 'redo',
        'repeat_old': 'history',
        'final_review': 'trophy'
    }
    
    return render_template(
        'lessons.html', 
        title='Уроки',
        modules=modules_data,
        lesson_types=lesson_types,
        lesson_icons=lesson_icons
    )

@app.route('/progress')
@login_required
def progress():
    db_sess = db_session.create_session()
    
    # Получаем прогресс пользователя
    user_progress = db_sess.query(UserProgress).filter(
        UserProgress.user_id == current_user.id
    ).all()
    
    # Получаем все модули
    modules = db_sess.query(Module).all()
    
    # Формируем данные для шаблона
    modules_progress = []
    total_correct = 0
    total_questions = 0
    completed_modules_count = 0
    
    for module in modules:
        progress = next((p for p in user_progress if p.module_id == module.id), None)
        
        if progress:
            total_correct += progress.correct_answers
            total_questions += progress.total_questions
            if progress.is_completed:
                completed_modules_count += 1
        
        modules_progress.append({
            'title': module.title,
            'description': module.description,
            'completion_percentage': progress.completion_percentage if progress else 0,
            'correct_answers': progress.correct_answers if progress else 0,
            'total_questions': progress.total_questions if progress else 0,
            'is_completed': progress.is_completed if progress else False,
            'last_activity': 'Сегодня'  # Здесь можно добавить реальные даты
        })
    
    # Рассчитываем общую статистику
    overall_accuracy = round((total_correct / total_questions * 100) if total_questions > 0 else 0, 1)
    
    return render_template(
        'progress.html',
        title='Прогресс',
        modules_progress=modules_progress,
        total_modules=len(modules),
        completed_modules=completed_modules_count,
        total_lessons=len(modules) * 4,  # 4 урока на модуль
        overall_accuracy=overall_accuracy
    )

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson(lesson_id):
    db_sess = db_session.create_session()
    
    # Получаем урок с подключением жестов
    lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        return redirect('/lessons')
    
    # Получаем модуль
    module = db_sess.query(Module).filter(Module.id == lesson.module_id).first()
    
    # Получаем жесты для этого урока с JOIN к таблице жестов
    lesson_gestures = db_sess.query(LessonGesture, Gesture).\
        join(Gesture, LessonGesture.gesture_id == Gesture.id).\
        filter(LessonGesture.lesson_id == lesson_id).\
        order_by(LessonGesture.order_index).all()
    
    # Если нет жестов для урока, возвращаем ошибку
    if not lesson_gestures:
        return render_template('error.html', message='Для этого урока нет жестов'), 404
    
    # Получаем GET-параметр question (номер текущего вопроса)
    current_question = request.args.get('question', 1, type=int)
    
    # Проверяем, что номер вопроса в пределах допустимого
    if current_question < 1 or current_question > len(lesson_gestures):
        current_question = 1
    
    # Получаем текущий жест
    lesson_gesture, gesture = lesson_gestures[current_question - 1]
    current_gesture_data = {
        'word': gesture.word,
        'video_filename': gesture.video_filename,
        'description': gesture.description,
        'module_title': module.title if module else 'Неизвестный модуль'
    }
    
    # Создаем варианты ответов
    correct_word = gesture.word
    options = [
        {'text': correct_word, 'is_correct': True},
        {'text': 'Дом', 'is_correct': False},
        {'text': 'Машина', 'is_correct': False},
        {'text': 'Солнце', 'is_correct': False}
    ]
    
    # Перемешиваем варианты ответов
    import random
    random.shuffle(options)
    
    total_questions = len(lesson_gestures)
    
    # URL для следующего вопроса
    next_question_url = None
    if current_question < total_questions:
        next_question_url = url_for('lesson', lesson_id=lesson_id, question=current_question + 1)
    else:
        next_question_url = url_for('lessons')
    
    templates = {
        'new_gestures': 'lesson_new_gestures.html',
        'repeat_new': 'lesson_repeat_new.html',
        'repeat_old': 'lesson_repeat_old.html',
        'final_review': 'lesson_final_review.html'
    }
    
    lesson_icons = {
        'new_gestures': 'star',
        'repeat_new': 'redo',
        'repeat_old': 'history',
        'final_review': 'trophy'
    }
    
    lesson_descriptions = {
        'new_gestures': 'Изучение новых жестов',
        'repeat_new': 'Закрепление материала',
        'repeat_old': 'Повторение пройденного',
        'final_review': 'Итоговый тест модуля'
    }
    
    template_name = templates.get(lesson.lesson_type, 'lesson_new_gestures.html')
    
    return render_template(
        template_name,
        lesson_title=lesson.title,
        lesson_description=lesson_descriptions.get(lesson.lesson_type, 'Урок'),
        module_title=module.title if module else 'Неизвестный модуль',
        lesson_icon=lesson_icons.get(lesson.lesson_type, 'star'),
        current_question=current_question,
        total_questions=total_questions,
        current_gesture=current_gesture_data,
        options=options,
        next_question_url=next_question_url,
        lesson_id=lesson_id
    )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

if __name__ == '__main__':
    app.run(host='0.0.0.0')