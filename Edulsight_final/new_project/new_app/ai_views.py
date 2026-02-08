from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta
from .models import (
    Student, Teacher, Attendance, WeeklyTest,
    PerformancePrediction, ImprovementStrategy,
    Notification, CareerRecommendationHistory
)
from .ml_models import PerformancePredictionModel, ImprovementStrategyGenerator
from .llm_integration import CareerRecommendationLLM, CourseRecommendationEngine
import json


@login_required
def predict_performance(request):
    """
    Predict student performance using ML model
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this feature.')
        return redirect('home')

    student = request.user.student

    # Gather student data
    attendance_data = Attendance.objects.filter(student=student)
    test_data = WeeklyTest.objects.filter(student=student)

    # Calculate metrics
    total_days = attendance_data.count()
    present_days = attendance_data.filter(status='Present').count()
    attendance_rate = (present_days / total_days * 100) if total_days > 0 else 0

    test_average = test_data.aggregate(Avg('score'))['score__avg'] or 0

    # Get grades data for assignments and participation
    from .models import Grade

    # Calculate assignments completed percentage based on assignment grades
    assignment_grades = Grade.objects.filter(
        student=student,
        grade_type='assignment'
    )
    assignments_completed = assignment_grades.aggregate(
        Avg('percentage')
    )['percentage__avg'] or test_average  # Use test average as fallback

    # Calculate participation score based on quiz scores
    quiz_grades = Grade.objects.filter(
        student=student,
        grade_type='quiz'
    )
    quiz_scores = quiz_grades.aggregate(
        Avg('percentage')
    )['percentage__avg'] or test_average  # Use test average as fallback

    # Calculate previous grade from all grades
    all_grades = Grade.objects.filter(student=student)
    previous_grade = all_grades.aggregate(
        Avg('percentage')
    )['percentage__avg'] or test_average

    # Estimate participation score from attendance and quiz performance
    participation_score = (attendance_rate * 0.5 + quiz_scores * 0.5)

    # Estimate study hours from performance metrics
    study_hours = min(10, max(2, (test_average / 10)))  # Scale 2-10 hours based on performance

    # Prepare data for ML model
    student_data = {
        'attendance_rate': attendance_rate,
        'test_average': test_average,
        'assignments_completed': assignments_completed,
        'participation_score': participation_score,
        'previous_grade': previous_grade,
        'study_hours': study_hours,
        'quiz_scores': quiz_scores
    }

    # Get prediction
    ml_model = PerformancePredictionModel()
    prediction_result = ml_model.predict_performance(student_data)

    # Save prediction to database
    prediction = PerformancePrediction.objects.create(
        student=student,
        predicted_grade=prediction_result['predicted_grade'],
        confidence_level=prediction_result['confidence'],
        trend=prediction_result['trend'],
        factors=student_data
    )

    # Generate improvement strategies
    strategy_generator = ImprovementStrategyGenerator()
    strategies = strategy_generator.generate_strategies(student_data, prediction_result)

    # Save strategies to database
    for strategy_text in strategies['strategies']:
        ImprovementStrategy.objects.create(
            student=student,
            strategy_text=strategy_text,
            priority='High' if strategies['strategies'].index(strategy_text) < 2 else 'Medium',
            category=strategies['priority_areas'][0] if strategies['priority_areas'] else 'general'
        )

    # Create notification
    Notification.objects.create(
        student=student,
        title='New Performance Prediction Available',
        message=f'Your predicted grade is {prediction_result["predicted_grade"]}% with {prediction_result["confidence"]} confidence. Your performance trend is {prediction_result["trend"]}.',
        notification_type='performance',
        priority='high' if prediction_result['predicted_grade'] < 60 else 'medium'
    )

    context = {
        'prediction': prediction_result,
        'strategies': strategies,
        'student_data': student_data,
        'recent_predictions': PerformancePrediction.objects.filter(
            student=student
        ).order_by('-prediction_date')[:5]
    }

    return render(request, 'performance_prediction.html', context)


@login_required
def advanced_career_recommendations(request):
    """
    Generate advanced career recommendations using LLM
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this feature.')
        return redirect('home')

    student = request.user.student

    # Gather student profile data
    from .models import Answer, Question
    answers = Answer.objects.filter(student=student)

    # Calculate performance metrics
    test_average = WeeklyTest.objects.filter(
        student=student
    ).aggregate(Avg('score'))['score__avg'] or 0

    # Get categories from questionnaire
    categories = []
    if answers.exists():
        category_scores = {}
        for answer in answers:
            cat = answer.question.category
            if cat not in category_scores:
                category_scores[cat] = []
            category_scores[cat].append(answer.score)

        # Calculate average scores per category
        for cat, scores in category_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score > 3:  # Threshold for interest
                categories.append(cat)

    student_profile = {
        'performance_grade': test_average,
        'strong_subjects': ['Mathematics', 'Science'],  # Can be enhanced
        'interests': categories[:3] if categories else ['Technology'],
        'skills': ['Problem Solving', 'Critical Thinking'],  # Can be enhanced
        'categories': categories[:2] if categories else ['Tech'],
        'test_average': test_average
    }

    # Generate recommendations using LLM
    llm = CareerRecommendationLLM()
    recommendations = llm.generate_career_recommendations(student_profile)

    # Generate course recommendations
    course_engine = CourseRecommendationEngine()
    current_performance = {
        'average_grade': test_average,
        'categories': categories[:2] if categories else ['Tech']
    }
    bridging_courses = course_engine.recommend_bridging_courses(
        current_performance,
        recommendations.get('careers', [])
    )

    # Save to history
    history = CareerRecommendationHistory.objects.create(
        student=student,
        careers=recommendations.get('careers', []),
        skills_recommended=recommendations.get('skills', []),
        courses_suggested=[course['course_name'] for course in bridging_courses],
        llm_used=llm.use_llm
    )

    # Create notification
    Notification.objects.create(
        student=student,
        title='New Career Recommendations Available',
        message=f'We have generated personalized career recommendations based on your profile. Top recommendation: {recommendations.get("careers", ["Various options"])[0] if recommendations.get("careers") else "Check your dashboard"}',
        notification_type='career',
        priority='medium'
    )

    context = {
        'recommendations': recommendations,
        'bridging_courses': bridging_courses,
        'student_profile': student_profile,
        'history': CareerRecommendationHistory.objects.filter(
            student=student
        ).order_by('-created_at')[:3]
    }

    return render(request, 'advanced_career_recommendations.html', context)


@login_required
def notifications_view(request):
    """
    Display all notifications for the user
    """
    notifications = []

    if hasattr(request.user, 'student'):
        notifications = Notification.objects.filter(
            student=request.user.student
        ).order_by('-created_at')
    elif hasattr(request.user, 'teacher'):
        notifications = Notification.objects.filter(
            teacher=request.user.teacher
        ).order_by('-created_at')

    # Mark notifications as read
    unread = notifications.filter(is_read=False)
    unread.update(is_read=True)

    context = {
        'notifications': notifications,
        'unread_count': unread.count()
    }

    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    notification = get_object_or_404(Notification, id=notification_id)

    # Check permission
    if hasattr(request.user, 'student') and notification.student == request.user.student:
        notification.is_read = True
        notification.save()
    elif hasattr(request.user, 'teacher') and notification.teacher == request.user.teacher:
        notification.is_read = True
        notification.save()

    return JsonResponse({'status': 'success'})


@login_required
def improvement_strategies_view(request):
    """
    Display and manage improvement strategies
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this feature.')
        return redirect('home')

    student = request.user.student

    if request.method == 'POST':
        strategy_id = request.POST.get('strategy_id')
        action = request.POST.get('action')

        strategy = get_object_or_404(ImprovementStrategy, id=strategy_id, student=student)

        if action == 'complete':
            strategy.completed = True
            strategy.save()
            messages.success(request, 'Strategy marked as completed!')
        elif action == 'dismiss':
            strategy.is_active = False
            strategy.save()
            messages.info(request, 'Strategy dismissed.')

    strategies = ImprovementStrategy.objects.filter(
        student=student,
        is_active=True
    ).order_by('-priority', '-created_at')

    completed_strategies = ImprovementStrategy.objects.filter(
        student=student,
        completed=True
    ).order_by('-created_at')[:5]

    context = {
        'active_strategies': strategies,
        'completed_strategies': completed_strategies,
        'completion_rate': (
            completed_strategies.count() /
            (strategies.count() + completed_strategies.count()) * 100
        ) if (strategies.count() + completed_strategies.count()) > 0 else 0
    }

    return render(request, 'improvement_strategies.html', context)


def create_automated_notifications():
    """
    Background task to create automated notifications
    Called by a scheduler (e.g., Celery beat)
    """
    from datetime import date
    today = date.today()

    # Check for low attendance
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

            if attendance_rate < 75:
                Notification.objects.create(
                    student=student,
                    title='Low Attendance Alert',
                    message=f'Your attendance is {attendance_rate:.1f}% in the last 7 days. Please improve your attendance to maintain good academic standing.',
                    notification_type='attendance',
                    priority='high'
                )

    # Check for declining test scores
    for student in students:
        recent_tests = WeeklyTest.objects.filter(
            student=student
        ).order_by('-test_date')[:3]

        if recent_tests.count() >= 3:
            scores = [test.score for test in recent_tests]
            if scores[0] < scores[1] < scores[2]:  # Declining trend
                Notification.objects.create(
                    student=student,
                    title='Performance Decline Alert',
                    message='Your recent test scores show a declining trend. Consider reviewing improvement strategies.',
                    notification_type='performance',
                    priority='high'
                )

    # Upcoming test reminders
    # This would require a TestSchedule model, which can be added later
    pass


@login_required
def performance_dashboard(request):
    """
    Enhanced performance dashboard with predictions and trends
    """
    if not hasattr(request.user, 'student'):
        messages.error(request, 'Only students can access this feature.')
        return redirect('home')

    student = request.user.student

    # Get recent predictions
    predictions = PerformancePrediction.objects.filter(
        student=student
    ).order_by('-prediction_date')[:10]

    # Get test scores over time
    test_scores = WeeklyTest.objects.filter(
        student=student
    ).order_by('test_date')

    # Get attendance data
    attendance_data = Attendance.objects.filter(
        student=student
    ).order_by('date')

    # Calculate metrics
    current_month_attendance = attendance_data.filter(
        date__month=datetime.now().month
    )
    attendance_rate = (
        current_month_attendance.filter(status='Present').count() /
        current_month_attendance.count() * 100
    ) if current_month_attendance.count() > 0 else 0

    # Prepare chart data
    chart_data = {
        'dates': [pred.prediction_date.strftime('%Y-%m-%d') for pred in predictions],
        'predicted_grades': [pred.predicted_grade for pred in predictions],
        'test_dates': [test.test_date.strftime('%Y-%m-%d') for test in test_scores],
        'test_scores': [test.score for test in test_scores]
    }

    # Get active strategies count
    active_strategies = ImprovementStrategy.objects.filter(
        student=student,
        is_active=True,
        completed=False
    ).count()

    # Get unread notifications count
    unread_notifications = Notification.objects.filter(
        student=student,
        is_read=False
    ).count()

    context = {
        'student': student,
        'latest_prediction': predictions.first() if predictions else None,
        'attendance_rate': attendance_rate,
        'test_average': test_scores.aggregate(Avg('score'))['score__avg'] or 0,
        'active_strategies': active_strategies,
        'unread_notifications': unread_notifications,
        'chart_data': json.dumps(chart_data),
        'recent_tests': test_scores.order_by('-test_date')[:5],
        'recent_attendance': attendance_data.order_by('-date')[:7]
    }

    return render(request, 'enhanced_dashboard.html', context)