from django.core.management.base import BaseCommand
from new_app.models import Career, Question, Option

class Command(BaseCommand):
    help = 'Populates the database with example careers and questions for Edulsight'

    def handle(self, *args, **kwargs):
        # Clear existing data (optional)
        # Career.objects.all().delete()
        # Question.objects.all().delete()
        # Option.objects.all().delete()

        # Add Careers
        careers = [
            {
                'name': 'Software Engineer',
                'description': 'Designs, develops, and maintains software applications, working with programming languages like Python, Java, and C++. Ideal for problem-solvers who enjoy coding and innovation.',
                'category': 'Tech'
            },
            {
                'name': 'Graphic Designer',
                'description': 'Creates visual content for branding, advertising, and media using tools like Adobe Photoshop and Illustrator. Perfect for creative individuals with an eye for aesthetics.',
                'category': 'Creative'
            },
            {
                'name': 'Data Analyst',
                'description': 'Interprets complex datasets to provide actionable business insights, using tools like Excel, SQL, and Tableau. Suited for those who love numbers and critical thinking.',
                'category': 'Analytical'
            },
            {
                'name': 'Project Manager',
                'description': 'Oversees projects, coordinating teams and resources to meet deadlines and goals. Requires strong leadership and communication skills, ideal for collaborative personalities.',
                'category': 'Collaborative'
            },
            {
                'name': 'Machine Learning Engineer',
                'description': 'Builds and deploys AI models to solve real-world problems, using frameworks like TensorFlow and PyTorch. Great for tech enthusiasts with a knack for innovation.',
                'category': 'Tech'
            },
            {
                'name': 'Content Writer',
                'description': 'Crafts engaging articles, blogs, and marketing copy for various platforms. Ideal for storytellers with excellent writing and creative skills.',
                'category': 'Creative'
            },
            {
                'name': 'Financial Analyst',
                'description': 'Analyzes financial data to guide investment decisions, using tools like Bloomberg Terminal and spreadsheets. Perfect for detail-oriented, analytical minds.',
                'category': 'Analytical'
            },
            {
                'name': 'Human Resources Specialist',
                'description': 'Manages recruitment, employee relations, and organizational development. Suited for those who excel in teamwork and interpersonal communication.',
                'category': 'Collaborative'
            },
            {
                'name': 'Cybersecurity Analyst',
                'description': 'Protects systems and networks from cyber threats, using tools like Wireshark and Splunk. Ideal for tech-savvy individuals passionate about security.',
                'category': 'Tech'
            },
            {
                'name': 'Video Editor',
                'description': 'Edits and produces video content for films, ads, or social media, using software like Adobe Premiere Pro. Great for creative professionals with a flair for storytelling.',
                'category': 'Creative'
            }
        ]

        for career_data in careers:
            career, created = Career.objects.get_or_create(
                name=career_data['name'],
                defaults={
                    'description': career_data['description'],
                    'category': career_data['category'],
                    'is_active': True
                }
            )
            self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Updated"} career: {career.name}'))

        # Add Questions
        questions = [
            {
                'text': 'Do you enjoy solving complex problems using code?',
                'category': 'Tech',
                'parent_question': None,
                'required_answer': None
            },
            {
                'text': 'Would you like to work on a team to develop a new software feature?',
                'category': 'Tech',
                'parent_question': 'Do you enjoy solving complex problems using code?',
                'required_answer': 4
            },
            {
                'text': 'Are you passionate about creating visual art or designs?',
                'category': 'Creative',
                'parent_question': None,
                'required_answer': None
            },
            {
                'text': 'Do you enjoy designing logos or branding materials?',
                'category': 'Creative',
                'parent_question': 'Are you passionate about creating visual art or designs?',
                'required_answer': 5
            },
            {
                'text': 'Do you find satisfaction in analyzing data to uncover trends?',
                'category': 'Analytical',
                'parent_question': None,
                'required_answer': None
            },
            {
                'text': 'Would you be interested in creating financial models for a company?',
                'category': 'Analytical',
                'parent_question': 'Do you find satisfaction in analyzing data to uncover trends?',
                'required_answer': 4
            },
            {
                'text': 'Do you thrive in collaborative team environments?',
                'category': 'Collaborative',
                'parent_question': None,
                'required_answer': None
            },
            {
                'text': 'Are you interested in leading a project team to achieve goals?',
                'category': 'Collaborative',
                'parent_question': 'Do you thrive in collaborative team environments?',
                'required_answer': 5
            },
            {
                'text': 'Are you curious about securing systems against cyber threats?',
                'category': 'Tech',
                'parent_question': None,
                'required_answer': None
            },
            {
                'text': 'Do you enjoy writing stories or creating content for audiences?',
                'category': 'Creative',
                'parent_question': None,
                'required_answer': None
            }
        ]

        question_objects = {}
        for question_data in questions:
            parent = None
            if question_data['parent_question']:
                parent = Question.objects.get(text=question_data['parent_question'])
            
            question, created = Question.objects.get_or_create(
                text=question_data['text'],
                defaults={
                    'category': question_data['category'],
                    'parent_question': parent,
                    'required_answer': question_data['required_answer'],
                    'is_active': True
                }
            )
            question_objects[question_data['text']] = question

            if created:
                # Add options
                for value, text in [
                    (1, 'Strongly Disagree'),
                    (2, 'Disagree'),
                    (3, 'Neutral'),
                    (4, 'Agree'),
                    (5, 'Strongly Agree')
                ]:
                    Option.objects.get_or_create(
                        question=question,
                        value=value,
                        defaults={'text': text}
                    )
            self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Updated"} question: {question.text}'))

        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))