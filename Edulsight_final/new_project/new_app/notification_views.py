from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Q
from .models import (
    Student, Teacher, ExamSchedule, Notification,
    PredictionFeedback, PerformancePrediction,
    CourseSuggestion, Grade, Attendance
)


@login_required
def student_course_suggestions(request):
    """
    View for students to see their course suggestions
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this page.')
        return redirect('home')

    student = request.user.student

    if request.method == 'POST':
        # Student providing feedback on a suggestion
        suggestion_id = request.POST.get('suggestion_id')
        action = request.POST.get('action')
        feedback = request.POST.get('feedback', '')

        suggestion = get_object_or_404(CourseSuggestion, id=suggestion_id, student=student)

        if action == 'accept':
            suggestion.is_accepted = True
            suggestion.student_feedback = feedback
            suggestion.save()
            messages.success(request, f'You have accepted the course: {suggestion.course_name}')

            # Notify teacher
            if suggestion.teacher:
                Notification.objects.create(
                    teacher=suggestion.teacher,
                    title='Course Suggestion Accepted',
                    message=f'{student.first_name} {student.last_name} has accepted your suggestion: {suggestion.course_name}',
                    notification_type='career',
                    priority='low'
                )

        elif action == 'decline':
            suggestion.is_accepted = False
            suggestion.student_feedback = feedback
            suggestion.save()
            messages.info(request, 'Course suggestion declined.')

    # Get all suggestions for this student
    suggestions = CourseSuggestion.objects.filter(student=student).order_by('-created_at')

    # Separate by priority
    critical = suggestions.filter(priority='critical')
    high = suggestions.filter(priority='high')
    medium = suggestions.filter(priority='medium')
    low = suggestions.filter(priority='low')

    context = {
        'critical_suggestions': critical,
        'high_suggestions': high,
        'medium_suggestions': medium,
        'low_suggestions': low,
        'total_suggestions': suggestions.count(),
        'accepted_count': suggestions.filter(is_accepted=True).count()
    }

    return render(request, 'student_course_suggestions.html', context)


@login_required
def prediction_feedback(request):
    """
    Allows students to provide feedback on prediction accuracy
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this page.')
        return redirect('home')

    student = request.user.student

    if request.method == 'POST':
        prediction_id = request.POST.get('prediction_id')
        accuracy = request.POST.get('accuracy_rating')
        usefulness = request.POST.get('usefulness_rating')
        comments = request.POST.get('comments', '')
        actual_grade = request.POST.get('actual_grade')

        prediction = get_object_or_404(PerformancePrediction, id=prediction_id, student=student)

        PredictionFeedback.objects.create(
            prediction=prediction,
            student=student,
            accuracy_rating=int(accuracy),
            usefulness_rating=int(usefulness),
            comments=comments,
            actual_grade=float(actual_grade) if actual_grade else None
        )

        messages.success(request, 'Thank you for your feedback! It helps us improve our predictions.')
        return redirect('prediction_feedback')

    # Get recent predictions
    predictions = PerformancePrediction.objects.filter(
        student=student
    ).order_by('-prediction_date')[:5]

    # Get predictions that haven't been given feedback
    predictions_with_feedback = PredictionFeedback.objects.filter(
        student=student
    ).values_list('prediction_id', flat=True)

    unfeedback_predictions = predictions.exclude(id__in=predictions_with_feedback)

    context = {
        'recent_predictions': predictions,
        'unfeedback_predictions': unfeedback_predictions,
        'feedback_count': PredictionFeedback.objects.filter(student=student).count()
    }

    return render(request, 'prediction_feedback.html', context)


@login_required
def exam_schedule_view(request):
    """
    View for teachers to create exam schedules and students to view them
    """
    if hasattr(request.user, 'teacher'):
        teacher = request.user.teacher

        if request.method == 'POST':
            subject = request.POST.get('subject')
            exam_type = request.POST.get('exam_type')
            exam_date = request.POST.get('exam_date')
            exam_time = request.POST.get('exam_time', '09:00')
            description = request.POST.get('description', '')
            student_ids = request.POST.getlist('students')

            # Combine date and time
            exam_datetime = datetime.strptime(f'{exam_date} {exam_time}', '%Y-%m-%d %H:%M')

            exam = ExamSchedule.objects.create(
                subject=subject,
                exam_type=exam_type,
                exam_date=exam_datetime,
                description=description,
                teacher=teacher
            )

            # Add students
            for student_id in student_ids:
                student = Student.objects.get(id=student_id)
                exam.students.add(student)

                # Create notification for each student
                Notification.objects.create(
                    student=student,
                    title=f'Upcoming {exam.get_exam_type_display()}',
                    message=f'{subject} {exam.get_exam_type_display()} scheduled for {exam_date} at {exam_time}',
                    notification_type='test',
                    priority='high'
                )

            messages.success(request, 'Exam schedule created and students notified!')
            return redirect('exam_schedule_view')

        # Get all students for the form
        students = Student.objects.filter(is_active=True)
        upcoming_exams = ExamSchedule.objects.filter(
            teacher=teacher,
            exam_date__gte=timezone.now()
        ).order_by('exam_date')

        context = {
            'students': students,
            'upcoming_exams': upcoming_exams,
            'is_teacher': True
        }

    elif hasattr(request.user, 'student'):
        student = request.user.student

        # Get upcoming exams for this student
        upcoming_exams = ExamSchedule.objects.filter(
            students=student,
            exam_date__gte=timezone.now()
        ).order_by('exam_date')

        context = {
            'upcoming_exams': upcoming_exams,
            'is_teacher': False
        }
    else:
        return redirect('home')

    return render(request, 'exam_schedule.html', context)


def send_automated_notifications():
    """
    Background task to send automated notifications
    Should be called by a scheduler (e.g., Celery)
    """
    from datetime import date, timedelta
    today = date.today()
    tomorrow = today + timedelta(days=1)
    week_later = today + timedelta(days=7)

    # 1. Exam reminders (24 hours before)
    upcoming_exams = ExamSchedule.objects.filter(
        exam_date__date=tomorrow,
        reminder_sent=False
    )

    for exam in upcoming_exams:
        for student in exam.students.all():
            Notification.objects.create(
                student=student,
                title=f'Exam Tomorrow: {exam.subject}',
                message=f'Reminder: {exam.subject} {exam.get_exam_type_display()} is tomorrow at {exam.exam_date.strftime("%H:%M")}',
                notification_type='test',
                priority='high'
            )
        exam.reminder_sent = True
        exam.save()

    # 2. Low attendance alerts
    students = Student.objects.filter(is_active=True)
    for student in students:
        recent_attendance = Attendance.objects.filter(
            student=student,
            date__gte=today - timedelta(days=7)
        )
        if recent_attendance.count() > 0:
            attendance_rate = recent_attendance.filter(
                status='Present'
            ).count() / recent_attendance.count() * 100

            if attendance_rate < 50:
                # Check if we already sent an alert this week
                recent_alert = Notification.objects.filter(
                    student=student,
                    notification_type='attendance',
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).exists()

                if not recent_alert:
                    Notification.objects.create(
                        student=student,
                        title='Critical Attendance Alert',
                        message=f'Your attendance is critically low at {attendance_rate:.1f}%. Immediate improvement required.',
                        notification_type='attendance',
                        priority='high'
                    )

    # 3. Performance decline alerts
    for student in students:
        recent_grades = Grade.objects.filter(
            student=student,
            date__gte=today - timedelta(days=30)
        ).order_by('-date')

        if recent_grades.count() >= 3:
            recent_avg = sum([g.percentage for g in recent_grades[:3]]) / 3
            older_grades = Grade.objects.filter(
                student=student,
                date__lt=today - timedelta(days=30)
            ).order_by('-date')[:3]

            if older_grades.count() >= 3:
                older_avg = sum([g.percentage for g in older_grades]) / 3

                if recent_avg < older_avg - 10:  # 10% decline
                    Notification.objects.create(
                        student=student,
                        title='Performance Decline Detected',
                        message=f'Your recent average ({recent_avg:.1f}%) shows a decline from previous performance ({older_avg:.1f}%). Consider reviewing improvement strategies.',
                        notification_type='performance',
                        priority='high'
                    )

    # 4. New course suggestion reminders
    unaccepted_suggestions = CourseSuggestion.objects.filter(
        is_accepted__isnull=True,
        created_at__gte=timezone.now() - timedelta(days=7),
        created_at__lt=timezone.now() - timedelta(days=3)
    )

    for suggestion in unaccepted_suggestions:
        # Check if reminder already sent
        recent_reminder = Notification.objects.filter(
            student=suggestion.student,
            message__contains=suggestion.course_name,
            created_at__gte=timezone.now() - timedelta(days=3)
        ).exists()

        if not recent_reminder:
            Notification.objects.create(
                student=suggestion.student,
                title='Pending Course Suggestion',
                message=f'Reminder: Please review the suggested course "{suggestion.course_name}" and provide your feedback.',
                notification_type='career',
                priority='medium'
            )

    return f"Automated notifications sent successfully at {timezone.now()}"