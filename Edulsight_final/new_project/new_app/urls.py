from django.urls import path
from . import views
from . import ai_views
from . import teacher_views
from . import notification_views

urlpatterns = [
    # General pages
    path('', views.home, name='home'),
    path('register/', views.register_student, name='register'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_student, name='logout'),

    # Dashboards
    path('student-dashboard/', views.student_dashboard, name='student_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),

    # Admin section
    path('answered-users/', views.answered_users, name='answered_users'),
    path('registered-users/', views.registered_users, name='registered_users'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-logout/', views.admin_logout, name='admin_logout'),
    path('manage-careers/', views.manage_careers, name='manage_careers'),
    path('analytics-dashboard/', views.analytics_dashboard, name='analytics_dashboard'),
    path('admin-login/', views.admin_login, name='admin_login'),
    path('registered-teachers/', views.registered_teachers, name='registered_teachers'), 

    # Questionnaire & results
    path('career-questionnaire/', views.career_questionnaire, name='career_questionnaire'),
    path('career-results/', views.career_results, name='career_results'),

    # Profile & feedback
    path('profile/', views.profile, name='profile'),
    path('submit-feedback/<int:career_id>/', views.submit_feedback, name='submit_feedback'),
    # ✅ Teacher operations (only one set, clean)
    path('teacher/attendance/<int:student_id>/', views.manage_attendance, name='manage_attendance'),
    path('teacher/tests/<int:student_id>/', views.manage_tests, name='manage_tests'),
    path('teacher/suggestions/<int:student_id>/', views.suggest_courses, name='suggest_courses'),

    # AI-Powered Features
    path('predict-performance/', ai_views.predict_performance, name='predict_performance'),
    path('advanced-career-recommendations/', ai_views.advanced_career_recommendations, name='advanced_career_recommendations'),
    path('notifications/', ai_views.notifications_view, name='notifications'),
    path('notification/<int:notification_id>/read/', ai_views.mark_notification_read, name='mark_notification_read'),
    path('improvement-strategies/', ai_views.improvement_strategies_view, name='improvement_strategies'),
    path('performance-dashboard/', ai_views.performance_dashboard, name='performance_dashboard'),

    # Teacher Grade & Feedback Management
    path('teacher/grades/', teacher_views.teacher_grade_management, name='teacher_grade_management'),
    path('teacher/analysis/<int:student_id>/', teacher_views.student_performance_analysis, name='student_performance_analysis'),
    path('teacher/feedback/', teacher_views.teacher_feedback_form, name='teacher_feedback_form'),

    # Student Views for Grades
    path('student/grades/', teacher_views.student_grades_view, name='student_grades_view'),

    # API for predictions
    path('api/predict/<int:student_id>/', teacher_views.performance_prediction_api, name='performance_prediction_api'),

    # Student Course Suggestions & Feedback
    path('student/course-suggestions/', notification_views.student_course_suggestions, name='student_course_suggestions'),
    path('student/prediction-feedback/', notification_views.prediction_feedback, name='prediction_feedback'),

    # Exam Schedule
    path('exam-schedule/', notification_views.exam_schedule_view, name='exam_schedule_view'),


]
