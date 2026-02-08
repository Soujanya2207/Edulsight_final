from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Sum
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import Student, Question, Option, Answer, Career, Feedback
from datetime import date, datetime, timedelta
import re
from django.contrib.auth.models import User
from .models import Attendance, WeeklyTest
from .models import Student, Teacher

# Student Views
def home(request):
    from .models import FAQ
    faqs = FAQ.objects.filter(is_active=True)

    # Group FAQs by category
    faq_categories = {}
    for faq in faqs:
        if faq.category not in faq_categories:
            faq_categories[faq.category] = []
        faq_categories[faq.category].append(faq)

    return render(request, 'home.html', {'faq_categories': faq_categories})

@login_required
def student_dashboard(request):
    student = request.user.student
    # Get top careers based on student's answers
    answers = Answer.objects.filter(student=student)
    categories = ['Tech', 'Creative', 'Analytical', 'Collaborative']
    careers = []
    
    if answers.exists():
        # Calculate score vector
        score_vector = [0] * len(categories)
        counts = [0] * len(categories)
        for answer in answers:
            try:
                idx = categories.index(answer.question.category)
                score_vector[idx] += answer.score
                counts[idx] += 1
            except ValueError:
                continue
        score_vector = [s / c if c > 0 else 0 for s, c in zip(score_vector, counts)]
        
        # Get top categories
        top_categories = sorted(
            [(score, cat) for score, cat in zip(score_vector, categories) if score > 0],
            reverse=True
        )[:2]
        
        # Fetch up to 3 careers from top categories
        for score, category in top_categories:
            category_careers = Career.objects.filter(category=category, is_active=True)[:3]
            careers.extend(category_careers)
    
    # Fallback to default careers if no answers or no matching careers
    if not careers:
        careers = Career.objects.filter(is_active=True)[:3]
    
    print(f"Dashboard careers for {student}: {len(careers)}")  # Debug
    return render(request, 'student_dashboard.html', {
        'student': student,
        'careers': careers
    })

from .models import Student, Teacher

def register_student(request):
    errors = {}
    success_message = None
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        date_of_birth = request.POST.get('date_of_birth')
        role = request.POST.get('role')

        if not first_name.isalpha():
            errors['first_name'] = "First name should only contain letters."
        if not last_name.isalpha():
            errors['last_name'] = "Last name should only contain letters."
        if len(password) < 6:
            errors['password'] = "Password must be at least 6 characters long."

        if not errors:
            if User.objects.filter(email=email).exists():
                errors['email'] = "Email already registered."
            else:
                user = User.objects.create_user(
                    username=email, email=email, password=password,
                    first_name=first_name, last_name=last_name
                )

                if role == 'student':
                    Student.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        date_of_birth=date_of_birth
                    )
                elif role == 'teacher':
                    Teacher.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        email=email
                    )

                success_message = f"{role.capitalize()} registered successfully!"

    return render(request, 'register.html', {
        'errors': errors,
        'success_message': success_message
    })

def login_user(request):
    errors = {}
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None and user.is_active:
                login(request, user)
                # Check if student
                if hasattr(user, 'student'):
                    return redirect('student_dashboard')
                # Check if teacher
                elif hasattr(user, 'teacher'):
                    return redirect('teacher_dashboard')
                # Check if admin
                elif user.is_staff:
                    return redirect('admin_dashboard')
                else:
                    errors['general'] = "User has no assigned role."
            else:
                errors['general'] = "Invalid credentials or inactive account."
        except User.DoesNotExist:
            errors['general'] = "Invalid credentials."
    return render(request, 'login.html', {'errors': errors})


def logout_student(request):
    logout(request)
    return redirect('home')

@login_required
def profile(request):
    student = request.user.student
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        if not User.objects.filter(email=email).exclude(id=student.user.id).exists():
            student.first_name = first_name
            student.last_name = last_name
            student.email = email
            student.user.email = email
            student.user.username = email
            student.user.save()
            student.save()
            messages.success(request, 'Profile updated.')
        else:
            messages.error(request, 'Email already in use.')
    return render(request, 'profile.html', {'student': student})

@login_required
def career_questionnaire(request):
    student = request.user.student
    answered_questions = Answer.objects.filter(student=student).values_list('question_id', flat=True)
    questions = cache.get('questions')
    if not questions:
        questions = Question.objects.filter(is_active=True)
        cache.set('questions', questions, 3600)
    
    print(f"Active questions: {questions.count()}, Answered: {len(answered_questions)}")  # Debug
    
    # Handle retake request
    if request.method == 'POST' and 'retake' in request.POST:
        print(f"Retaking questionnaire for student: {student}")  # Debug
        Answer.objects.filter(student=student).delete()
        cache.delete('questions')  # Clear cache
        messages.success(request, 'Questionnaire reset. Start answering again.')
        return redirect('career_questionnaire')

    next_question = None
    for question in questions:
        if question.id not in answered_questions:
            if not question.parent_question:
                next_question = question
                break
            else:
                parent_answer = Answer.objects.filter(student=student, question=question.parent_question).first()
                if parent_answer and parent_answer.score >= question.required_answer:
                    next_question = question
                    break
    
    if request.method == 'POST' and 'question_id' in request.POST:
        question_id = request.POST.get('question_id')
        score = request.POST.get('score')
        print(f"POST data: question_id={question_id}, score={score}")  # Debug
        try:
            question = Question.objects.get(id=question_id, is_active=True)
            if not Answer.objects.filter(student=student, question=question).exists():
                Answer.objects.create(
                    student=student,
                    question=question,
                    score=int(score)
                )
                print(f"Answer saved: question={question.text}, score={score}")  # Debug
            # Refresh answered questions
            answered_questions = Answer.objects.filter(student=student).values_list('question_id', flat=True)
            remaining_questions = Question.objects.filter(is_active=True).exclude(id__in=answered_questions)
            print(f"Remaining questions: {remaining_questions.count()}")  # Debug
            if not remaining_questions.exists():
                return redirect('career_results')
        except Question.DoesNotExist:
            messages.error(request, 'Question not found.')
            print(f"Question not found: ID={question_id}")  # Debug
        except ValueError:
            messages.error(request, 'Invalid score. Please select a valid option.')
            print(f"Invalid score: {score}")  # Debug
        return redirect('career_questionnaire')

    print(f"Next question: {next_question.text if next_question else 'None'}")  # Debug
    return render(request, 'career_questionnaire.html', {
        'question': next_question,
        'options': next_question.options.all() if next_question else [],
        'no_questions': not next_question and questions.exists()
    })

@login_required
def career_results(request):
    student = request.user.student
    # Handle retake request
    if request.method == 'POST' and 'retake' in request.POST:
        print(f"Retaking questionnaire for student: {student}")  # Debug
        Answer.objects.filter(student=student).delete()
        cache.delete('questions')  # Clear cache
        messages.success(request, 'Questionnaire reset. Start answering again.')
        return redirect('career_questionnaire')

    # Get student's answers
    answers = Answer.objects.filter(student=student)
    print(f"Found {answers.count()} answers")  # Debug
    
    # Initialize variables
    careers = []
    message = None
    categories = ['Tech', 'Creative', 'Analytical', 'Collaborative']
    
    if not answers.exists():
        message = 'No answers found. Please complete the questionnaire or retake it.'
    else:
        # Calculate score vector
        score_vector = [0] * len(categories)
        counts = [0] * len(categories)
        for answer in answers:
            try:
                idx = categories.index(answer.question.category)
                score_vector[idx] += answer.score
                counts[idx] += 1
            except ValueError:
                print(f"Invalid category for question {answer.question.id}: {answer.question.category}")
                continue
        score_vector = [s / c if c > 0 else 0 for s, c in zip(score_vector, counts)]
        print(f"Score vector: {score_vector}")  # Debug

        # Get top categories
        top_categories = sorted(
            [(score, cat) for score, cat in zip(score_vector, categories) if score > 0],
            reverse=True
        )[:2]
        print(f"Top categories: {top_categories}")  # Debug

        if not top_categories:
            message = 'No valid scores. Please retake the questionnaire.'
            careers = Career.objects.filter(is_active=True)[:3]
            print(f"Default careers: {careers.count()}")  # Debug
        else:
            # Fetch careers from top categories
            for score, category in top_categories:
                category_careers = Career.objects.filter(category=category, is_active=True)[:3]
                print(f"Careers in {category}: {category_careers.count()}")  # Debug
                careers.extend(category_careers)

        if not careers:
            message = 'No careers found for your top categories. Please retake the questionnaire.'
            careers = Career.objects.filter(is_active=True)[:3]
            print(f"Fallback careers: {careers.count()}")  # Debug

    return render(request, 'career_results.html', {
        'careers': careers,
        'message': message
    })

@login_required
def reset_questionnaire(request):
    if request.method == 'POST':
        Answer.objects.filter(student=request.user.student).delete()
        messages.success(request, 'Questionnaire reset.')
        return redirect('career_questionnaire')
    return render(request, 'reset_questionnaire.html')

@login_required
def submit_feedback(request, career_id):
    try:
        career = Career.objects.get(id=career_id, is_active=True)
        if request.method == 'POST':
            rating = request.POST.get('rating')
            comment = request.POST.get('comment')
            print(f"Feedback submitted: rating={rating}, comment={comment}")  # Debug
            Feedback.objects.create(
                student=request.user.student,
                career=career,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, 'Feedback submitted.')
            return redirect('career_results')
        return render(request, 'submit_feedback.html', {'career': career})
    except Career.DoesNotExist:
        messages.error(request, 'Career not found.')
        print(f"Career not found: ID={career_id}")  # Debug
        return redirect('career_results')

# Admin Views
def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Invalid credentials or not an admin.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid credentials.')
    return render(request, 'admin1/admin_login.html')

@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    questions = Question.objects.filter(is_active=True)
    all_questions = Question.objects.filter(is_active=True)
    errors = {}

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            text = request.POST.get('text')
            category = request.POST.get('category')
            parent_question_id = request.POST.get('parent_question')
            required_answer = request.POST.get('required_answer')

            if not text:
                errors['text'] = 'Question text is required.'
            if category not in ['Tech', 'Creative', 'Analytical', 'Collaborative']:
                errors['category'] = 'Invalid category.'
            if required_answer and (not required_answer.isdigit() or not 1 <= int(required_answer) <= 5):
                errors['required_answer'] = 'Required answer must be between 1 and 5.'

            if not errors:
                try:
                    question = Question.objects.create(
                        text=text,
                        category=category,
                        parent_question=Question.objects.get(id=parent_question_id) if parent_question_id else None,
                        required_answer=int(required_answer) if required_answer else None
                    )
                    for value, text in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
                        Option.objects.create(question=question, text=text, value=value)
                    cache.delete('questions')
                    messages.success(request, 'Question added successfully.')
                except Exception as e:
                    errors['general'] = str(e)

        elif action == 'edit':
            question_id = request.POST.get('question_id')
            text = request.POST.get('text')
            category = request.POST.get('category')
            parent_question_id = request.POST.get('parent_question')
            required_answer = request.POST.get('required_answer')

            if not text:
                errors['text'] = 'Question text is required.'
            if category not in ['Tech', 'Creative', 'Analytical', 'Collaborative']:
                errors['category'] = 'Invalid category.'
            if required_answer and (not required_answer.isdigit() or not 1 <= int(required_answer) <= 5):
                errors['required_answer'] = 'Required answer must be between 1 and 5.'

            if not errors:
                try:
                    question = Question.objects.get(id=question_id)
                    question.text = text
                    question.category = category
                    question.parent_question = Question.objects.get(id=parent_question_id) if parent_question_id else None
                    question.required_answer = int(required_answer) if required_answer else None
                    question.save()
                    cache.delete('questions')
                    messages.success(request, 'Question updated successfully.')
                except Question.DoesNotExist:
                    errors['general'] = 'Question not found.'
                except Exception as e:
                    errors['general'] = str(e)

        elif action == 'delete':
            question_id = request.POST.get('question_id')
            try:
                Question.objects.filter(id=question_id).update(is_active=False)
                cache.delete('questions')
                messages.success(request, 'Question deleted successfully.')
            except Question.DoesNotExist:
                errors['general'] = 'Question not found.'

    return render(request, 'admin1/dashboard.html', {
        'questions': questions,
        'all_questions': all_questions,
        'errors': errors
    })

@login_required
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

@login_required
def registered_users(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    students = Student.objects.filter(is_active=True).order_by('-created_at')
    total_users = students.count()
    return render(request, 'admin1/registered_users.html', {
        'total_users': total_users,
        'students': students
    })

@login_required
def answered_users(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    answered_students = Student.objects.filter(answer__isnull=False, is_active=True) \
        .annotate(total_score=Sum('answer__score')).distinct()
    return render(request, 'admin1/answered_users.html', {
        'answered_users': answered_students.count(),
        'students': answered_students
    })

@login_required
def manage_careers(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    careers = cache.get('careers')
    if not careers:
        careers = Career.objects.filter(is_active=True)
        cache.set('careers', careers, 3600)
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add':
                name = request.POST.get('name')
                description = request.POST.get('description')
                category = request.POST.get('category')
                if not name or not description or not category:
                    messages.error(request, 'All fields are required.')
                else:
                    Career.objects.create(name=name, description=description, category=category)
                    messages.success(request, 'Career added.')
            elif action == 'edit':
                career_id = request.POST.get('career_id')
                career = Career.objects.get(id=career_id)
                career.name = request.POST.get('name')
                career.description = request.POST.get('description')
                career.category = request.POST.get('category')
                if not career.name or not career.description or not career.category:
                    messages.error(request, 'All fields are required.')
                else:
                    career.save()
                    messages.success(request, 'Career updated.')
            elif action == 'delete':
                career_id = request.POST.get('career_id')
                Career.objects.filter(id=career_id).update(is_active=False)
                messages.success(request, 'Career deleted.')
            cache.delete('careers')
        except Career.DoesNotExist:
            messages.error(request, 'Career not found.')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    return render(request, 'admin1/manage_careers.html', {'careers': careers})

@login_required
def analytics_dashboard(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    categories = Answer.objects.values('question__category').annotate(avg_score=Avg('score'))
    chart_data = {
        'labels': [cat['question__category'] for cat in categories],
        'data': [cat['avg_score'] for cat in categories]
    }
    return render(request, 'admin1/analytics_dashboard.html', {'chart_data': chart_data})

@login_required
def export_student_report(request, student_id):
    if not request.user.is_staff:
        return redirect('admin_login')
    try:
        student = Student.objects.get(id=student_id)
        answers = Answer.objects.filter(student=student)
        categories = ['Tech', 'Creative', 'Analytical', 'Collaborative']
        careers = []

        if answers.exists():
            # Calculate score vector
            score_vector = [0] * len(categories)
            counts = [0] * len(categories)
            for answer in answers:
                try:
                    idx = categories.index(answer.question.category)
                    score_vector[idx] += answer.score
                    counts[idx] += 1
                except ValueError:
                    continue
            score_vector = [s / c if c > 0 else 0 for s, c in zip(score_vector, counts)]
            
            # Get top categories
            top_categories = sorted(
                [(score, cat) for score, cat in zip(score_vector, categories) if score > 0],
                reverse=True
            )[:2]
            
            # Fetch careers
            for score, category in top_categories:
                category_careers = Career.objects.filter(category=category, is_active=True)[:3]
                for career in category_careers:
                    careers.append({'career': career, 'score': min(score * 20, 100.0)})
        
        # Fallback to default careers
        if not careers:
            careers = [{'career': career, 'score': 50.0} for career in Career.objects.filter(is_active=True)[:3]]

        # Generate PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{student.id}.pdf"'
        p = canvas.Canvas(response, pagesize=letter)
        p.drawString(100, 750, f"Career Report for {student.first_name} {student.last_name}")
        p.drawString(100, 730, f"Generated on: {date.today().strftime('%Y-%m-%d')}")
        y = 700
        for item in careers:
            career = item['career']
            score = item['score']
            p.drawString(100, y, f"{career.name}: {score:.1f}%")
            desc = career.description[:100] + '...' if len(career.description) > 100 else career.description
            p.drawString(100, y-20, desc)
            y -= 40
        p.showPage()
        p.save()
        return response
    except Student.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('registered_users')
    

@login_required
def teacher_dashboard(request):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')
    teacher = request.user.teacher
    students = Student.objects.filter(is_active=True).order_by('-created_at')  # Fetch all active students

    # Calculate average test scores and attendance for each student (only for this teacher)
    from django.db.models import Avg, Count, Q

    students_data = []
    for student in students:
        # Calculate average test score (only tests given by this teacher)
        avg_test_score = WeeklyTest.objects.filter(student=student, teacher=teacher).aggregate(Avg('score'))['score__avg']

        # Calculate attendance percentage (only attendance marked by this teacher)
        total_attendance = Attendance.objects.filter(student=student, teacher=teacher).count()
        present_count = Attendance.objects.filter(student=student, teacher=teacher, status='Present').count()
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0

        students_data.append({
            'student': student,
            'avg_test_score': avg_test_score if avg_test_score else 0,
            'attendance_rate': attendance_rate
        })

    return render(request, 'teacher_dashboard.html', {
        'teacher': teacher,
        'students': students,
        'students_data': students_data
    })

def auto_generate_course_suggestions(student):
    """
    Automatically generate course suggestions based on grades and attendance
    """
    from .models import Grade, CourseSuggestion, Notification, Attendance, WeeklyTest

    # Calculate attendance percentage
    total_attendance = Attendance.objects.filter(student=student).count()
    present_count = Attendance.objects.filter(student=student, status='Present').count()
    attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 100

    # Calculate grade average
    grades = Grade.objects.filter(student=student)
    grade_avg = grades.aggregate(Avg('percentage'))['percentage__avg'] or 0

    # Get test average
    test_avg = WeeklyTest.objects.filter(student=student).aggregate(Avg('score'))['score__avg'] or 0

    # Generate suggestions based on performance
    if attendance_rate < 75 or grade_avg < 60:
        # Check if suggestion doesn't already exist
        existing = CourseSuggestion.objects.filter(
            student=student,
            created_at__gte=datetime.now() - timedelta(days=7)  # Check last 7 days
        )

        if attendance_rate < 75 and not existing.filter(course_name__icontains='attendance').exists():
            priority = 'critical' if attendance_rate < 50 else 'high'
            CourseSuggestion.objects.create(
                student=student,
                teacher=None,  # Auto-generated
                course_name='Time Management & Attendance Improvement Program',
                course_description='Structured program to improve attendance and time management skills',
                reason=f'Current attendance is {attendance_rate:.1f}%. Target: 75%+',
                priority=priority,
                subject_area='General',
                target_improvement='Increase attendance to 75%',
                based_on_grade=grade_avg,
                based_on_attendance=attendance_rate
            )

            # Notify student
            Notification.objects.create(
                student=student,
                title='Course Suggestion Based on Attendance',
                message=f'Your attendance is {attendance_rate:.1f}%. A support program has been recommended.',
                notification_type='career',
                priority='high'
            )

        if grade_avg < 60 and grade_avg > 0 and not existing.filter(course_name__icontains='foundation').exists():
            priority = 'critical' if grade_avg < 40 else 'high'
            CourseSuggestion.objects.create(
                student=student,
                teacher=None,
                course_name='Foundation Strengthening Course',
                course_description='Comprehensive course to strengthen fundamental concepts',
                reason=f'Current average grade is {grade_avg:.1f}%. Target: 60%+',
                priority=priority,
                subject_area='Core Subjects',
                target_improvement='Improve grades to 60%',
                based_on_grade=grade_avg,
                based_on_attendance=attendance_rate
            )

            Notification.objects.create(
                student=student,
                title='Course Suggestion Based on Grades',
                message=f'Your average grade is {grade_avg:.1f}%. A foundation course has been recommended.',
                notification_type='career',
                priority='high'
            )

    # Subject-specific suggestions
    if grades.exists():
        subjects = grades.values('subject').annotate(avg_grade=Avg('percentage'))
        for subj in subjects:
            if subj['avg_grade'] < 50:  # Critical subject performance
                existing_subj = CourseSuggestion.objects.filter(
                    student=student,
                    subject_area=subj['subject'],
                    created_at__gte=datetime.now() - timedelta(days=7)
                ).exists()

                if not existing_subj:
                    CourseSuggestion.objects.create(
                        student=student,
                        teacher=None,
                        course_name=f'{subj["subject"]} Remedial Program',
                        course_description=f'Focused program to improve {subj["subject"]} performance',
                        reason=f'Current {subj["subject"]} average: {subj["avg_grade"]:.1f}%',
                        priority='critical',
                        subject_area=subj['subject'],
                        target_improvement=f'Improve {subj["subject"]} to 60%+',
                        based_on_grade=subj['avg_grade'],
                        based_on_attendance=attendance_rate
                    )


@login_required
def manage_attendance(request, student_id):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')

    student = Student.objects.get(id=student_id)
    teacher = request.user.teacher

    if request.method == "POST":
        status = request.POST.get("status")
        Attendance.objects.create(student=student, teacher=teacher, status=status)
        messages.success(request, f"Attendance marked for {student.first_name}.")

        # Auto-generate course suggestions based on new attendance data
        auto_generate_course_suggestions(student)

        return redirect('teacher_dashboard')

    attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    return render(request, "attendance_list.html", {
        "student": student,
        "attendance_records": attendance_records
    })


@login_required
def manage_tests(request, student_id):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')

    student = Student.objects.get(id=student_id)
    teacher = request.user.teacher

    if request.method == "POST":
        score = request.POST.get("score")
        WeeklyTest.objects.create(student=student, teacher=teacher, score=score)
        messages.success(request, f"Test score added for {student.first_name}.")

        # Auto-generate course suggestions based on new test data
        auto_generate_course_suggestions(student)

        return redirect('teacher_dashboard')

    test_records = WeeklyTest.objects.filter(student=student).order_by('-test_date')
    return render(request, "test_scores.html", {
        "student": student,
        "test_records": test_records
    })


@login_required
def suggest_courses(request, student_id):
    if not hasattr(request.user, 'teacher'):
        return redirect('login')

    student = Student.objects.get(id=student_id)

    # Simple rule: if attendance < 75% or avg score < 50, suggest extra courses
    total_classes = Attendance.objects.filter(student=student).count()
    present_classes = Attendance.objects.filter(student=student, status="Present").count()
    avg_score = WeeklyTest.objects.filter(student=student).aggregate(Avg("score"))['score__avg'] or 0

    attendance_percent = (present_classes / total_classes * 100) if total_classes > 0 else 0

    # Import models here
    from .models import Grade, CourseSuggestion, Notification
    teacher = request.user.teacher if hasattr(request.user, 'teacher') else None

    if request.method == 'POST' and teacher:
        # Manual course suggestion by teacher
        course_name = request.POST.get('course_name')
        description = request.POST.get('description')
        reason = request.POST.get('reason')
        priority = request.POST.get('priority', 'medium')
        subject_area = request.POST.get('subject_area')

        CourseSuggestion.objects.create(
            student=student,
            teacher=teacher,
            course_name=course_name,
            course_description=description,
            reason=reason,
            priority=priority,
            subject_area=subject_area,
            target_improvement=request.POST.get('target', ''),
            based_on_grade=avg_score,
            based_on_attendance=attendance_percent
        )

        # Send notification to student
        Notification.objects.create(
            student=student,
            title='New Course Suggestion',
            message=f'Your teacher has suggested: {course_name}',
            notification_type='career',
            priority='medium'
        )
        messages.success(request, 'Course suggestion added successfully!')
        return redirect('suggest_courses', student_id=student_id)

    # Get grades if available
    grades = Grade.objects.filter(student=student)
    grade_avg = grades.aggregate(Avg('percentage'))['percentage__avg'] or avg_score

    # Auto-generate smart suggestions based on performance
    suggestions = []

    # Attendance-based suggestions
    if attendance_percent < 75:
        priority = 'critical' if attendance_percent < 50 else 'high'
        suggestions.append({
            'course': 'Time Management & Study Skills',
            'reason': f'Attendance is {attendance_percent:.1f}%. Regular attendance is crucial.',
            'priority': priority,
            'type': 'auto'
        })

    # Grade-based suggestions
    if grade_avg < 60:
        priority = 'critical' if grade_avg < 40 else 'high'
        suggestions.append({
            'course': 'Foundation Course in Core Subjects',
            'reason': f'Average grade is {grade_avg:.1f}%. Strengthening fundamentals needed.',
            'priority': priority,
            'type': 'auto'
        })
    elif grade_avg > 85:
        suggestions.append({
            'course': 'Advanced Placement Program',
            'reason': f'Excellent performance ({grade_avg:.1f}%). Ready for advanced topics.',
            'priority': 'low',
            'type': 'auto'
        })

    # Subject-specific suggestions
    if grades.exists():
        subjects = grades.values('subject').annotate(avg_grade=Avg('percentage'))
        for subj in subjects:
            if subj['avg_grade'] < 60:
                suggestions.append({
                    'course': f'{subj["subject"]} Support Program',
                    'reason': f'Below average in {subj["subject"]} ({subj["avg_grade"]:.1f}%)',
                    'priority': 'high' if subj['avg_grade'] < 50 else 'medium',
                    'type': 'auto'
                })

    # Get existing suggestions from database
    existing_suggestions = CourseSuggestion.objects.filter(student=student).order_by('-created_at')

    return render(request, "course_suggestions.html", {
        "student": student,
        "attendance_percent": attendance_percent,
        "avg_score": avg_score,
        "grade_average": grade_avg,
        "suggestions": suggestions,
        "existing_suggestions": existing_suggestions
    })

@login_required
def registered_teachers(request):
    teachers = Teacher.objects.all()
    total_teachers = teachers.count()
    return render(request, "admin1/registered_teachers.html", {
        "teachers": teachers,
        "total_teachers": total_teachers
    })

