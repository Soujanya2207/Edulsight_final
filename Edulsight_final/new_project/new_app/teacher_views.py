from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta, date
from .models import (
    Student, Teacher, Attendance, WeeklyTest, Grade,
    Feedback, PerformancePrediction, Notification
)
from .ml_models import PerformancePredictionModel
import json


@login_required
def teacher_grade_management(request):
    """
    Allows teachers to add and manage student grades
    """
    if not hasattr(request.user, 'teacher'):
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')

    teacher = request.user.teacher

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        subject = request.POST.get('subject')
        grade_type = request.POST.get('grade_type')
        score = float(request.POST.get('score'))
        max_score = float(request.POST.get('max_score', 100))
        comments = request.POST.get('comments', '')

        student = get_object_or_404(Student, id=student_id)

        Grade.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
            grade_type=grade_type,
            score=score,
            max_score=max_score,
            comments=comments
        )

        # Create notification for student
        Notification.objects.create(
            student=student,
            title='New Grade Posted',
            message=f'You have received a new grade in {subject}: {score}/{max_score}',
            notification_type='performance',
            priority='medium'
        )

        # Import and call the auto-suggestion function
        from .views import auto_generate_course_suggestions
        auto_generate_course_suggestions(student)

        messages.success(request, 'Grade added successfully!')
        return redirect('teacher_grade_management')

    # Get all students
    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')

    # Get recent grades added by this teacher
    recent_grades = Grade.objects.filter(
        teacher=teacher
    ).order_by('-date')[:10]

    context = {
        'teacher': teacher,
        'students': students,
        'recent_grades': recent_grades
    }

    return render(request, 'teacher_grade_management.html', context)


@login_required
def student_performance_analysis(request, student_id):
    """
    Shows detailed performance analysis with graphs for a specific student
    Based on attendance and test scores only
    """
    if not hasattr(request.user, 'teacher'):
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')

    teacher = request.user.teacher
    student = get_object_or_404(Student, id=student_id)

    # Get attendance data
    attendance_data = Attendance.objects.filter(student=student, teacher=teacher).order_by('date')
    total_days = attendance_data.count()
    present_days = attendance_data.filter(status='Present').count()
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0

    # Get test scores
    test_scores = WeeklyTest.objects.filter(student=student, teacher=teacher).order_by('test_date')
    test_average = test_scores.aggregate(Avg('score'))['score__avg'] or 0

    # Prepare data for ML prediction (using only attendance and test scores)
    student_data = {
        'attendance_rate': attendance_rate,
        'test_average': test_average,
        'assignments_completed': 0,
        'participation_score': 0,
        'previous_grade': test_average,
        'study_hours': 0,
        'quiz_scores': 0
    }

    # Get prediction
    ml_model = PerformancePredictionModel()
    prediction = ml_model.predict_performance(student_data)

    # Test scores trend chart
    test_chart_data = {
        'labels': [test.test_date.strftime('%Y-%m-%d') for test in test_scores],
        'datasets': [{
            'label': 'Test Score',
            'data': [test.score for test in test_scores],
            'borderColor': 'rgb(99, 102, 241)',
            'backgroundColor': 'rgba(99, 102, 241, 0.1)',
            'tension': 0.1,
            'fill': True
        }]
    }

    # Attendance trend (all attendance records)
    attendance_chart_data = {
        'labels': [att.date.strftime('%Y-%m-%d') for att in attendance_data],
        'datasets': [{
            'label': 'Attendance',
            'data': [1 if att.status == 'Present' else 0 for att in attendance_data],
            'backgroundColor': ['rgba(34, 197, 94, 0.7)' if att.status == 'Present' else 'rgba(239, 68, 68, 0.7)' for att in attendance_data]
        }]
    }

    context = {
        'student': student,
        'teacher': teacher,
        'attendance_rate': attendance_rate,
        'test_average': test_average,
        'total_tests': test_scores.count(),
        'present_days': present_days,
        'total_days': total_days,
        'prediction': prediction,
        'test_chart_data': json.dumps(test_chart_data),
        'attendance_chart_data': json.dumps(attendance_chart_data),
        'test_scores': test_scores,
        'attendance_data': attendance_data
    }

    return render(request, 'student_performance_analysis.html', context)


@login_required
def teacher_feedback_form(request):
    """
    Comprehensive feedback form with all contact details
    """
    if not hasattr(request.user, 'teacher'):
        messages.error(request, 'Only teachers can access this page.')
        return redirect('home')

    teacher = request.user.teacher

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        feedback_type = request.POST.get('feedback_type')
        comment = request.POST.get('comment')

        # Student contact info
        student_phone = request.POST.get('student_phone')
        student_address = request.POST.get('student_address')

        # Parent contact info
        parent_name = request.POST.get('parent_name')
        parent_phone = request.POST.get('parent_phone')
        parent_email = request.POST.get('parent_email')

        # Teacher contact info
        teacher_phone = request.POST.get('teacher_phone')
        subject = request.POST.get('subject')

        student = get_object_or_404(Student, id=student_id)

        Feedback.objects.create(
            student=student,
            teacher=teacher,
            comment=comment,
            feedback_type=feedback_type,
            student_phone=student_phone,
            student_address=student_address,
            parent_name=parent_name,
            parent_phone=parent_phone,
            parent_email=parent_email,
            teacher_phone=teacher_phone,
            subject=subject
        )

        # Notify student
        Notification.objects.create(
            student=student,
            title='New Feedback from Teacher',
            message=f'{teacher.first_name} {teacher.last_name} has provided feedback on your {feedback_type} performance.',
            notification_type='performance',
            priority='medium'
        )

        messages.success(request, 'Feedback submitted successfully!')
        return redirect('teacher_feedback_form')

    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')
    recent_feedback = Feedback.objects.filter(teacher=teacher).order_by('-created_at')[:5]

    context = {
        'teacher': teacher,
        'students': students,
        'recent_feedback': recent_feedback
    }

    return render(request, 'teacher_feedback_form.html', context)


@login_required
def student_grades_view(request):
    """
    View for students to see their grades and attendance
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this page.')
        return redirect('home')

    student = request.user.student

    # Get all grades
    grades = Grade.objects.filter(student=student).order_by('-date')

    # Get attendance records
    attendance = Attendance.objects.filter(student=student).order_by('-date')[:30]

    # Calculate attendance rate
    total_days = attendance.count()
    present_days = attendance.filter(status='Present').count()
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0

    # Group grades by subject
    subjects = grades.values_list('subject', flat=True).distinct()
    grades_by_subject = {}
    for subject in subjects:
        subject_grades = grades.filter(subject=subject)
        grades_by_subject[subject] = {
            'grades': subject_grades,
            'average': subject_grades.aggregate(Avg('percentage'))['percentage__avg']
        }

    # Get feedback from teachers
    feedback = Feedback.objects.filter(student=student, teacher__isnull=False).order_by('-created_at')

    context = {
        'student': student,
        'grades': grades,
        'attendance': attendance,
        'attendance_rate': attendance_rate,
        'grades_by_subject': grades_by_subject,
        'feedback': feedback
    }

    return render(request, 'student_grades_view.html', context)


def performance_prediction_api(request, student_id):
    """
    API endpoint for getting performance predictions
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    student = get_object_or_404(Student, id=student_id)

    # Check permission
    if hasattr(request.user, 'teacher') or (hasattr(request.user, 'student') and request.user.student == student):
        # Get data
        grades = Grade.objects.filter(student=student)
        attendance = Attendance.objects.filter(student=student)
        tests = WeeklyTest.objects.filter(student=student)

        # Calculate metrics
        attendance_rate = attendance.filter(status='Present').count() / attendance.count() * 100 if attendance.count() > 0 else 0
        grade_avg = grades.aggregate(Avg('percentage'))['percentage__avg'] or 0
        test_avg = tests.aggregate(Avg('score'))['score__avg'] or 0

        # Prepare ML data
        student_data = {
            'attendance_rate': attendance_rate,
            'test_average': test_avg,
            'assignments_completed': 85,
            'participation_score': 75,
            'previous_grade': grade_avg,
            'study_hours': 5,
            'quiz_scores': 80
        }

        # Get prediction
        ml_model = PerformancePredictionModel()
        prediction = ml_model.predict_performance(student_data)

        # Save prediction
        PerformancePrediction.objects.create(
            student=student,
            predicted_grade=prediction['predicted_grade'],
            confidence_level=prediction['confidence'],
            trend=prediction['trend'],
            factors=student_data
        )

        return JsonResponse({
            'prediction': prediction,
            'current_metrics': {
                'attendance_rate': attendance_rate,
                'grade_average': grade_avg,
                'test_average': test_avg
            }
        })
    else:
        return JsonResponse({'error': 'Permission denied'}, status=403)