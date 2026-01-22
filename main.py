from flask import Flask, render_template, redirect, request, jsonify
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
from data.user_lesson import UserLesson  
import random
from datetime import datetime


db_session.global_init("db/app.db")

app = Flask(__name__)
app.config['SECRET_KEY'] = '65432456uijhgfdsxcvbn'
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    try:
        return db_sess.query(User).get(int(user_id))
    finally:
        db_sess.close()

@app.route("/")
def index():
    return render_template("index.html", title='')

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title='Профиль')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form, message='Пароли не совпадают')
        db_sess = db_session.create_session()
        try:
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
            
            # Создаем начальный прогресс для пользователя
            modules = db_sess.query(Module).all()
            for module in modules:
                progress = UserProgress(
                    user_id=user.id,
                    module_id=module.id,
                    correct_answers=0,
                    total_questions=0,
                    completion_percentage=0.0,
                    is_completed=False
                )
                db_sess.add(progress)
                
                # НЕ создаем запись UserLesson для первого урока
                # Запись создастся только когда пользователь начнет урок
                
            db_sess.commit()
            
            login_user(user)
            return redirect('/')
        finally:
            db_sess.close()
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).filter(User.email == form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/")
            return render_template('login.html',
                                   message="Неправильный логин или пароль",
                                   form=form)
        finally:
            db_sess.close()
    return render_template('login.html', title='Авторизация', form=form)

def get_lesson_status(user_id, lesson_id):
    """Проверяет статус урока: пройден, доступен, заблокирован"""
    db_sess = db_session.create_session()
    try:
        # Получаем урок
        lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return {'available': False, 'completed': False}
        
        # Проверяем, есть ли запись об уроке
        user_lesson = db_sess.query(UserLesson).filter(
            UserLesson.user_id == user_id,
            UserLesson.lesson_id == lesson_id
        ).first()
        
        if user_lesson:
            # Проверяем пройден ли урок
            completed = user_lesson.completed_at is not None
            # Если есть запись - урок доступен (пройден или нет)
            return {'available': True, 'completed': completed}
        
        # Если записи нет - проверяем, доступен ли урок
        # Получаем все уроки модуля
        module_lessons = db_sess.query(Lesson).filter(
            Lesson.module_id == lesson.module_id
        ).order_by(Lesson.order_index).all()
        
        # Находим индекс текущего урока
        current_index = -1
        for i, module_lesson in enumerate(module_lessons):
            if module_lesson.id == lesson_id:
                current_index = i
                break
        
        if current_index == -1:
            return {'available': False, 'completed': False}
        
        # Первый урок всегда доступен
        if current_index == 0:
            # Урок доступен, но НЕ СОЗДАЕМ запись, пока пользователь не начнет его
            return {'available': True, 'completed': False}
        
        # Для остальных уроков проверяем, пройден ли предыдущий урок
        prev_lesson = module_lessons[current_index - 1]
        prev_user_lesson = db_sess.query(UserLesson).filter(
            UserLesson.user_id == user_id,
            UserLesson.lesson_id == prev_lesson.id
        ).first()
        
        # Урок доступен только если предыдущий ПРОЙДЕН
        if prev_user_lesson and prev_user_lesson.completed_at is not None:
            return {'available': True, 'completed': False}
        
        return {'available': False, 'completed': False}
    finally:
        db_sess.close()

@app.route('/lessons')
@login_required
def lessons():
    db_sess = db_session.create_session()
    try:
        modules = db_sess.query(Module).order_by(Module.order_index).all()
        
        modules_data = []
        for module in modules:
            lessons_list = db_sess.query(Lesson).filter(
                Lesson.module_id == module.id
            ).order_by(Lesson.order_index).all()
            
            user_progress = db_sess.query(UserProgress).filter(
                UserProgress.user_id == current_user.id,
                UserProgress.module_id == module.id
            ).first()
            
            # Убедись, что прогресс есть и обновлен
            if user_progress:
                # Пересчитываем прогресс на всякий случай
                total_lessons_in_module = db_sess.query(Lesson).filter(
                    Lesson.module_id == module.id
                ).count()
                
                if total_lessons_in_module > 0:
                    completed_lessons = db_sess.query(UserLesson).join(Lesson).filter(
                        UserLesson.user_id == current_user.id,
                        UserLesson.completed_at.isnot(None),
                        Lesson.module_id == module.id
                    ).count()
                    
                    progress_per_lesson = 100.0 / total_lessons_in_module
                    user_progress.completion_percentage = min(100.0, completed_lessons * progress_per_lesson)
                    db_sess.commit()
            
            progress_percentage = user_progress.completion_percentage if user_progress else 0
            
            lessons_data = []
            for lesson in lessons_list:
                # Получаем статус урока
                status = get_lesson_status(current_user.id, lesson.id)
                
                lessons_data.append({
                    'id': lesson.id,
                    'title': lesson.title,
                    'lesson_type': lesson.lesson_type,
                    'available': status['available'],
                    'completed': status['completed']
                })
            
            modules_data.append({
                'id': module.id,
                'title': module.title,
                'description': module.description,
                'progress_percentage': round(progress_percentage),  # Округляем для отображения
                'lessons': lessons_data
            })
        
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
    finally:
        db_sess.close()

@app.route('/progress')
@login_required
def progress():
    db_sess = db_session.create_session()
    try:
        user_progress = db_sess.query(UserProgress).filter(
            UserProgress.user_id == current_user.id
        ).all()
        
        modules = db_sess.query(Module).order_by(Module.order_index).all()
        
        modules_progress = []
        total_correct = 0
        total_questions = 0
        completed_modules_count = 0
        
        #проверяем совпадение модуля с текущим
        for module in modules:
            progress = next((p for p in user_progress if p.module_id == module.id), None)
            
            if progress:
                total_correct += progress.correct_answers
                total_questions += progress.total_questions
                if progress.is_completed:
                    completed_modules_count += 1
            
            # Подсчитываем пройденные уроки в модуле
            completed_lessons_in_module = 0
            total_lessons_in_module = db_sess.query(Lesson).filter(
                Lesson.module_id == module.id
            ).count()
            
            if total_lessons_in_module > 0:
                completed_lessons_in_module = db_sess.query(UserLesson).join(Lesson).filter(
                    UserLesson.user_id == current_user.id,
                    UserLesson.completed_at.isnot(None),
                    Lesson.module_id == module.id
                ).count()
                
                # Пересчитываем процент завершения (25% за каждый урок)
                if progress and not progress.is_completed:
                    progress_per_lesson = 100.0 / total_lessons_in_module
                    progress.completion_percentage = min(100.0, completed_lessons_in_module * progress_per_lesson)
                    db_sess.commit()
            
            modules_progress.append({
                'title': module.title,
                'description': module.description,
                'completion_percentage': progress.completion_percentage if progress else 0,
                'correct_answers': progress.correct_answers if progress else 0,
                'total_questions': progress.total_questions if progress else 0,
                'is_completed': progress.is_completed if progress else False,
                'last_activity': 'Сегодня',
                'completed_lessons': completed_lessons_in_module,
                'total_lessons': total_lessons_in_module
            })
        
        overall_accuracy = round((total_correct / total_questions * 100) if total_questions > 0 else 0, 1)
        
        return render_template(
            'progress.html',
            title='Прогресс',
            modules_progress=modules_progress,
            total_modules=len(modules),
            completed_modules=completed_modules_count,
            total_lessons=sum(m['total_lessons'] for m in modules_progress),
            overall_accuracy=overall_accuracy
        )
    finally:
        db_sess.close()

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson(lesson_id):
    db_sess = db_session.create_session()
    try:
        # Проверяем доступность урока
        status = get_lesson_status(current_user.id, lesson_id)
        if not status['available']:
            return redirect('/lessons')
        
        # Получаем урок
        lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return redirect('/lessons')
        
        # Получаем жесты для этого урока
        lesson_gestures = db_sess.query(LessonGesture).filter(
            LessonGesture.lesson_id == lesson_id
        ).order_by(LessonGesture.order_index).all()
        
        if not lesson_gestures:
            return redirect('/lessons')
        
        # Получаем информацию о жестах
        gestures_info = []
        for lg in lesson_gestures:
            gesture = db_sess.query(Gesture).filter(Gesture.id == lg.gesture_id).first()
            if gesture:
                gestures_info.append({
                    'lesson_gesture': lg,
                    'gesture': gesture
                })
        
        if not gestures_info:
            return redirect('/lessons')
        
        current_question = request.args.get('question', 1, type=int)
        
        if current_question < 1 or current_question > len(gestures_info):
            current_question = 1
        
        # Получаем текущий жест
        current_item = gestures_info[current_question - 1]
        gesture = current_item['gesture']
        
        
        current_gesture_data = {
            'word': gesture.word,
            'video_filename': gesture.video_filename,  # Только имя файла
            'description': gesture.description,
            'gesture_id': gesture.id
        }
        
        # Создаем варианты ответов
        options = [
            {'text': gesture.word, 'is_correct': True},
            {'text': 'Дом', 'is_correct': False},
            {'text': 'Машина', 'is_correct': False},
            {'text': 'Солнце', 'is_correct': False}
        ]
        
        random.shuffle(options)
        
        total_questions = len(gestures_info)
        
        # URL для следующего вопроса
        next_question_url = None
        if current_question < total_questions:
            next_question_url = url_for('lesson', lesson_id=lesson_id, question=current_question + 1)
        else:
            next_question_url = url_for('finish_lesson', lesson_id=lesson_id)
        
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
            module_title='Модуль',
            lesson_icon=lesson_icons.get(lesson.lesson_type, 'star'),
            current_question=current_question,
            total_questions=total_questions,
            current_gesture=current_gesture_data,
            options=options,
            next_question_url=next_question_url,
            lesson_id=lesson_id
        )
    finally:
        db_sess.close()

@app.route('/finish_lesson/<int:lesson_id>')
@login_required
def finish_lesson(lesson_id):
    """Завершает урок и открывает доступ к следующему уроку"""
    db_sess = db_session.create_session()
    try:
        # Получаем урок
        lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return redirect('/lessons')
        
        # Отмечаем текущий урок как завершенный
        user_lesson = db_sess.query(UserLesson).filter(
            UserLesson.user_id == current_user.id,
            UserLesson.lesson_id == lesson_id
        ).first()
        
        if not user_lesson:
            user_lesson = UserLesson(
                user_id=current_user.id,
                lesson_id=lesson_id,
                completed_at=datetime.now()
            )
            db_sess.add(user_lesson)
        else:
            user_lesson.completed_at = datetime.now()
        
        # Находим следующий урок В ТОМ ЖЕ МОДУЛЕ
        next_lesson = db_sess.query(Lesson).filter(
            Lesson.module_id == lesson.module_id,
            Lesson.order_index == lesson.order_index
        ).first()
        
        if next_lesson:
            # Проверяем, есть ли уже запись о следующем уроке
            next_user_lesson = db_sess.query(UserLesson).filter(
                UserLesson.user_id == current_user.id,
                UserLesson.lesson_id == next_lesson.id
            ).first()
            
            # Создаем запись для следующего урока, если ее нет
            if not next_user_lesson:
                next_user_lesson = UserLesson(
                    user_id=current_user.id,
                    lesson_id=next_lesson.id,
                    completed_at=None
                )
                db_sess.add(next_user_lesson)
        
        # Обновляем прогресс модуля
        user_progress = db_sess.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.module_id == lesson.module_id
        ).first()
        
        if user_progress:
            # Считаем сколько уроков в модуле всего
            total_lessons_in_module = db_sess.query(Lesson).filter(
                Lesson.module_id == lesson.module_id
            ).count()
            
            # Считаем сколько уроков пройдено
            completed_lessons = db_sess.query(UserLesson).join(Lesson).filter(
                UserLesson.user_id == current_user.id,
                UserLesson.completed_at.isnot(None),
                Lesson.module_id == lesson.module_id
            ).count()
            
            # Увеличиваем прогресс: каждый урок = +25% (100% / 4 урока = 25% за урок)
            # Но если в модуле другое количество уроков, считаем пропорционально
            if total_lessons_in_module > 0:
                progress_per_lesson = 100.0 / total_lessons_in_module
                new_progress = min(100.0, completed_lessons * progress_per_lesson)
                
                # Принудительно обновляем прогресс
                user_progress.completion_percentage = new_progress
                print(f"Обновлен прогресс модуля {lesson.module_id}: {completed_lessons}/{total_lessons_in_module} уроков = {new_progress}%")
            
            # Если это финальный урок модуля
            if lesson.lesson_type == 'final_review':
                user_progress.is_completed = True
                user_progress.completion_percentage = 100.0
        
        db_sess.commit()
        
        return redirect('/lessons')
        
    except Exception as e:
        print(f"Ошибка при завершении урока: {e}")
        db_sess.rollback()
        return redirect('/lessons')
    finally:
        db_sess.close()

@app.route('/errors')
@login_required
def errors():
    """Страница с ошибками пользователя"""
    db_sess = db_session.create_session()
    
    mistakes = db_sess.query(UserMistake).filter(
        UserMistake.user_id == current_user.id
    ).all()
    
    mistakes_data = []
    for mistake in mistakes:
        gesture = db_sess.query(Gesture).filter(Gesture.id == mistake.gesture_id).first()
        if gesture:
            mistakes_data.append({
                'gesture_word': gesture.word,
                'incorrect_answer': mistake.incorrect_answer,
                'mistake_count': mistake.mistake_count,
                'gesture_id': gesture.id
            })
    
    return render_template('errors.html', 
                          title='Мои ошибки',
                          mistakes=mistakes_data)

def save_mistake(user_id, gesture_id, lesson_id, incorrect_answer):
    """Сохраняет ошибку пользователя"""
    db_sess = db_session.create_session()
    try:
        # Проверяем, есть ли уже такая ошибка
        existing_mistake = db_sess.query(UserMistake).filter(
            UserMistake.user_id == user_id,
            UserMistake.gesture_id == gesture_id,
            UserMistake.lesson_id == lesson_id
        ).first()
        
        if existing_mistake:
            # Увеличиваем счетчик ошибок
            existing_mistake.mistake_count += 1
            if incorrect_answer:
                existing_mistake.incorrect_answer = incorrect_answer
        else:
            # Получаем модуль для урока
            lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
            module_id = lesson.module_id if lesson else None
            
            # Создаем новую запись об ошибке
            mistake = UserMistake(
                user_id=user_id,
                gesture_id=gesture_id,
                lesson_id=lesson_id,
                module_id=module_id,
                incorrect_answer=incorrect_answer,
                mistake_count=1
            )
            db_sess.add(mistake)
        
        db_sess.commit()
        return True
    except Exception as e:
        print(f"Ошибка при сохранении ошибки: {e}")
        db_sess.rollback()
        return False
    finally:
        db_sess.close()

@app.route('/save_answer', methods=['POST'])
@login_required
def save_answer():
    """Сохраняет ответ пользователя и ошибки если есть"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400
            
        lesson_id = data.get('lesson_id')
        gesture_id = data.get('gesture_id')
        is_correct = data.get('is_correct')
        selected_answer = data.get('selected_answer')  # Добавь это поле в JavaScript
        
        db_sess = db_session.create_session()
        
        # Получаем урок
        lesson = db_sess.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            db_sess.close()
            return jsonify({'success': False, 'error': 'Урок не найден'}), 404
        
        # Получаем жест
        gesture = db_sess.query(Gesture).filter(Gesture.id == gesture_id).first()
        
        # Если ответ неправильный - сохраняем ошибку
        if not is_correct and gesture and selected_answer:
            save_mistake(current_user.id, gesture_id, lesson_id, selected_answer)
        
        # Сохраняем или обновляем запись об уроке
        user_lesson = db_sess.query(UserLesson).filter(
            UserLesson.user_id == current_user.id,
            UserLesson.lesson_id == lesson_id
        ).first()
        
        if not user_lesson:
            user_lesson = UserLesson(
                user_id=current_user.id,
                lesson_id=lesson_id,
                total_answers=1,
                correct_answers=1 if is_correct else 0
            )
            db_sess.add(user_lesson)
        else:
            user_lesson.total_answers += 1
            if is_correct:
                user_lesson.correct_answers += 1
        
        # Обновляем прогресс пользователя
        user_progress = db_sess.query(UserProgress).filter(
            UserProgress.user_id == current_user.id,
            UserProgress.module_id == lesson.module_id
        ).first()
        
        if user_progress:
            user_progress.total_questions += 1
            if is_correct:
                user_progress.correct_answers += 1
            
            # Пересчитываем процент завершения
            total_lessons_in_module = db_sess.query(Lesson).filter(
                Lesson.module_id == lesson.module_id
            ).count()
            
            if total_lessons_in_module > 0:
                # Подсчитываем, сколько уроков в модуле пройдено
                completed_lessons = db_sess.query(UserLesson).join(Lesson).filter(
                    UserLesson.user_id == current_user.id,
                    UserLesson.completed_at.isnot(None),
                    Lesson.module_id == lesson.module_id
                ).count()
                
                user_progress.completion_percentage = min(
                    100.0,
                    (completed_lessons / total_lessons_in_module) * 100
                )
            
            db_sess.commit()
        
        db_sess.close()
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Ошибка при сохранении ответа: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")

if __name__ == '__main__':
    app.run(port=8025, host='127.0.0.1', debug=True)