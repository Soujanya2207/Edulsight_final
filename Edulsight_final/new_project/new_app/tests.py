from django.test import TestCase, Client
from django.contrib.auth.models import User
from new_app.models import Student, Question, Option, Answer, Career, CareerRecommendation
from django.urls import reverse

class CareerResultsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student@example.com', password='test123')
        self.student = Student.objects.create(
            user=self.user,
            first_name='Test',
            last_name='Student',
            email='student@example.com',
            date_of_birth='2000-01-01'
        )
        self.career = Career.objects.create(
            name='Software Engineer',
            description='Develops software',
            category='Tech',
            is_active=True
        )
        self.question = Question.objects.create(
            text='Do you enjoy coding?',
            category='Tech',
            is_active=True
        )
        for value, text in [(1, 'Strongly Disagree'), (2, 'Disagree'), (3, 'Neutral'), (4, 'Agree'), (5, 'Strongly Agree')]:
            Option.objects.create(question=self.question, text=text, value=value)
        self.client.login(username='student@example.com', password='test123')

    def test_results_no_answers(self):
        response = self.client.get(reverse('career_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No recommendations')

    def test_results_with_answers(self):
        response = self.client.post(
            reverse('career_questionnaire'),
            {'question_id': self.question.id, 'score': 5}
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        response = self.client.get(reverse('career_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Software Engineer')
        self.assertTrue(CareerRecommendation.objects.filter(student=self.student).exists())