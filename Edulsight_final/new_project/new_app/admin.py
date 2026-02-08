from django.contrib import admin
from .models import (
    Student, Teacher, Question, Option, Answer, Career,
    Feedback, Attendance, WeeklyTest, PerformancePrediction,
    ImprovementStrategy, Notification, CareerRecommendationHistory,
    Grade, FAQ, CourseSuggestion, ExamSchedule, PredictionFeedback
)

# Register models for Django admin (NOT the custom admin1)
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'is_active', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']
    list_filter = ['is_active', 'created_at']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'subject']
    search_fields = ['first_name', 'last_name', 'email']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'category', 'is_active']
    list_filter = ['category', 'is_active']

@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['category', 'is_active']

@admin.register(PerformancePrediction)
class PerformancePredictionAdmin(admin.ModelAdmin):
    list_display = ['student', 'predicted_grade', 'confidence_level', 'trend', 'prediction_date']
    list_filter = ['confidence_level', 'trend', 'prediction_date']
    date_hierarchy = 'prediction_date'

@admin.register(ImprovementStrategy)
class ImprovementStrategyAdmin(admin.ModelAdmin):
    list_display = ['student', 'category', 'priority', 'is_active', 'completed', 'created_at']
    list_filter = ['priority', 'is_active', 'completed', 'category']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read']
    date_hierarchy = 'created_at'

@admin.register(CareerRecommendationHistory)
class CareerRecommendationHistoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'llm_used', 'created_at', 'feedback_rating']
    list_filter = ['llm_used', 'created_at']
    date_hierarchy = 'created_at'

# Register Grade model
@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ['student', 'teacher', 'subject', 'grade_type', 'score', 'percentage', 'date']
    list_filter = ['subject', 'grade_type', 'date']
    search_fields = ['student__first_name', 'student__last_name', 'subject']

# Register FAQ model
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_active', 'order', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']
    ordering = ['order', 'created_at']

# Register CourseSuggestion
@admin.register(CourseSuggestion)
class CourseSuggestionAdmin(admin.ModelAdmin):
    list_display = ['course_name', 'student', 'teacher', 'priority', 'is_accepted', 'created_at']
    list_filter = ['priority', 'is_accepted', 'subject_area', 'created_at']
    search_fields = ['course_name', 'student__first_name', 'student__last_name']

# Register ExamSchedule
@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ['subject', 'exam_type', 'exam_date', 'teacher', 'reminder_sent']
    list_filter = ['exam_type', 'exam_date', 'reminder_sent']
    date_hierarchy = 'exam_date'

# Register PredictionFeedback
@admin.register(PredictionFeedback)
class PredictionFeedbackAdmin(admin.ModelAdmin):
    list_display = ['student', 'accuracy_rating', 'usefulness_rating', 'created_at']
    list_filter = ['accuracy_rating', 'usefulness_rating', 'created_at']

# Register other models
admin.site.register(Option)
admin.site.register(Answer)
admin.site.register(Feedback)
admin.site.register(Attendance)
admin.site.register(WeeklyTest)
