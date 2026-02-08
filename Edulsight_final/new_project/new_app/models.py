from django.db import models
from django.contrib.auth.models import User

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Question(models.Model):
    text = models.TextField()
    category = models.CharField(max_length=50)
    parent_question = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    required_answer = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

class Option(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    value = models.IntegerField()

class Answer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    score = models.IntegerField()

class Career(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

class Feedback(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    career = models.ForeignKey(Career, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(null=True, blank=True)
    comment = models.TextField(blank=True)
    # Contact Information
    student_phone = models.CharField(max_length=20, blank=True)
    student_address = models.TextField(blank=True)
    parent_name = models.CharField(max_length=100, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_email = models.EmailField(blank=True)
    teacher_phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    feedback_type = models.CharField(max_length=50, choices=[
        ('academic', 'Academic'),
        ('behavioral', 'Behavioral'),
        ('career', 'Career'),
        ('general', 'General')
    ], default='general')
    created_at = models.DateTimeField(auto_now_add=True)

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)  # allow NULL for now
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    subject = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)   # <— this is new
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent')])


    def __str__(self):
        return f"{self.student.first_name} - {self.date} ({self.status})"


class WeeklyTest(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, null=True, blank=True)  # NEW
    test_date = models.DateField(auto_now_add=True)
    score = models.IntegerField()

    def __str__(self):
        return f"{self.student.first_name} - {self.score}"


class PerformancePrediction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    predicted_grade = models.FloatField()
    actual_grade = models.FloatField(null=True, blank=True)
    prediction_date = models.DateTimeField(auto_now_add=True)
    confidence_level = models.CharField(max_length=20, choices=[
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low')
    ])
    trend = models.CharField(max_length=20, choices=[
        ('Improving', 'Improving'),
        ('Stable', 'Stable'),
        ('Declining', 'Declining')
    ])
    factors = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.student.first_name} - Predicted: {self.predicted_grade}%"


class ImprovementStrategy(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    strategy_text = models.TextField()
    priority = models.CharField(max_length=20, choices=[
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low')
    ])
    category = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.first_name} - {self.category}"


class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('performance', 'Performance Alert'),
        ('attendance', 'Attendance Alert'),
        ('test', 'Test Reminder'),
        ('career', 'Career Update'),
        ('improvement', 'Improvement Suggestion'),
        ('deadline', 'Deadline Reminder')
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    ], default='medium')

    def __str__(self):
        user = self.student or self.teacher
        return f"{user} - {self.title}"

    class Meta:
        ordering = ['-created_at']


class CareerRecommendationHistory(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    careers = models.JSONField()
    skills_recommended = models.JSONField()
    courses_suggested = models.JSONField()
    llm_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    feedback_rating = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.first_name} - {self.created_at.date()}"


class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    grade_type = models.CharField(max_length=50, choices=[
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('assignment', 'Assignment'),
        ('project', 'Project')
    ])
    score = models.FloatField()
    max_score = models.FloatField(default=100)
    percentage = models.FloatField()
    date = models.DateField(auto_now_add=True)
    comments = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.percentage = (self.score / self.max_score) * 100
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.first_name} - {self.subject} - {self.grade_type}"


class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=100, choices=[
        ('general', 'General'),
        ('academic', 'Academic'),
        ('career', 'Career Guidance'),
        ('technical', 'Technical Support'),
        ('registration', 'Registration')
    ])
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.question[:50]


class CourseSuggestion(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, null=True, blank=True)
    course_name = models.CharField(max_length=200)
    course_description = models.TextField()
    reason = models.TextField(help_text="Why this course is suggested based on performance")
    priority = models.CharField(max_length=20, choices=[
        ('critical', 'Critical - Immediate attention needed'),
        ('high', 'High - Important for improvement'),
        ('medium', 'Medium - Recommended'),
        ('low', 'Low - Optional enhancement')
    ])
    # Performance metrics that triggered this suggestion
    based_on_grade = models.FloatField(null=True, blank=True)
    based_on_attendance = models.FloatField(null=True, blank=True)
    subject_area = models.CharField(max_length=100)
    target_improvement = models.CharField(max_length=200)
    resources_link = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_accepted = models.BooleanField(default=False, null=True, blank=True)
    student_feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at', 'priority']

    def __str__(self):
        return f"{self.course_name} for {self.student.first_name}"


class ExamSchedule(models.Model):
    subject = models.CharField(max_length=100)
    exam_type = models.CharField(max_length=50, choices=[
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm'),
        ('final', 'Final'),
        ('assignment', 'Assignment Due'),
        ('project', 'Project Due')
    ])
    exam_date = models.DateTimeField()
    description = models.TextField(blank=True)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    students = models.ManyToManyField(Student)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.exam_type} on {self.exam_date.date()}"


class PredictionFeedback(models.Model):
    prediction = models.ForeignKey(PerformancePrediction, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    accuracy_rating = models.IntegerField(choices=[
        (1, 'Very Inaccurate'),
        (2, 'Inaccurate'),
        (3, 'Somewhat Accurate'),
        (4, 'Accurate'),
        (5, 'Very Accurate')
    ])
    usefulness_rating = models.IntegerField(choices=[
        (1, 'Not Useful'),
        (2, 'Slightly Useful'),
        (3, 'Moderately Useful'),
        (4, 'Useful'),
        (5, 'Very Useful')
    ])
    comments = models.TextField(blank=True)
    actual_grade = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.student.first_name}'s prediction"



