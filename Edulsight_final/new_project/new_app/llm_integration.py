import os
import json
from typing import List, Dict
from django.conf import settings

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class CareerRecommendationLLM:
    def __init__(self):
        # Initialize OpenAI API (can be replaced with local LLM)
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        if OPENAI_AVAILABLE and self.api_key:
            openai.api_key = self.api_key
        self.use_llm = OPENAI_AVAILABLE and bool(self.api_key)

    def generate_career_recommendations(self, student_profile: Dict) -> Dict:
        """
        Generate personalized career recommendations using LLM
        """
        if not self.use_llm:
            return self._fallback_recommendations(student_profile)

        try:
            prompt = self._create_recommendation_prompt(student_profile)

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert career counselor specializing in student guidance."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            recommendations = self._parse_llm_response(response.choices[0].message.content)
            return recommendations

        except Exception as e:
            print(f"LLM Error: {e}")
            return self._fallback_recommendations(student_profile)

    def _create_recommendation_prompt(self, student_profile: Dict) -> str:
        """
        Create a detailed prompt for LLM
        """
        prompt = f"""
        Based on the following student profile, provide personalized career recommendations:

        Student Profile:
        - Academic Performance: {student_profile.get('performance_grade', 'N/A')}%
        - Strong Subjects: {', '.join(student_profile.get('strong_subjects', []))}
        - Interests: {', '.join(student_profile.get('interests', []))}
        - Skills: {', '.join(student_profile.get('skills', []))}
        - Career Preference Categories: {', '.join(student_profile.get('categories', []))}
        - Test Scores Average: {student_profile.get('test_average', 'N/A')}%

        Please provide:
        1. Top 3 career recommendations with explanations
        2. Required skills for each career
        3. Suggested courses or certifications
        4. Industry trends and job market outlook
        5. Potential salary ranges

        Format the response as structured JSON.
        """
        return prompt

    def _parse_llm_response(self, response: str) -> Dict:
        """
        Parse LLM response into structured format
        """
        try:
            # Attempt to parse JSON response
            return json.loads(response)
        except:
            # Parse text response
            lines = response.strip().split('\n')
            recommendations = {
                'careers': [],
                'skills': [],
                'courses': [],
                'trends': '',
                'additional_insights': ''
            }

            current_section = None
            for line in lines:
                line = line.strip()
                if 'career' in line.lower() or 'recommendation' in line.lower():
                    current_section = 'careers'
                elif 'skill' in line.lower():
                    current_section = 'skills'
                elif 'course' in line.lower() or 'certification' in line.lower():
                    current_section = 'courses'
                elif line and current_section:
                    if current_section == 'careers' and line.startswith(('1.', '2.', '3.', '-', '•')):
                        recommendations['careers'].append(line.lstrip('1234567890.- •'))
                    elif current_section == 'skills' and line.startswith(('-', '•')):
                        recommendations['skills'].append(line.lstrip('- •'))
                    elif current_section == 'courses' and line.startswith(('-', '•')):
                        recommendations['courses'].append(line.lstrip('- •'))

            return recommendations

    def _fallback_recommendations(self, student_profile: Dict) -> Dict:
        """
        Provide fallback recommendations when LLM is not available
        """
        categories = student_profile.get('categories', ['Tech'])
        performance = student_profile.get('performance_grade', 70)

        career_map = {
            'Tech': {
                'high': ['Software Engineer', 'Data Scientist', 'AI/ML Engineer'],
                'medium': ['Web Developer', 'IT Support Specialist', 'QA Engineer'],
                'low': ['Technical Writer', 'IT Support', 'Digital Marketing']
            },
            'Creative': {
                'high': ['UX/UI Designer', 'Creative Director', 'Product Designer'],
                'medium': ['Graphic Designer', 'Content Creator', 'Video Editor'],
                'low': ['Social Media Manager', 'Content Writer', 'Marketing Assistant']
            },
            'Analytical': {
                'high': ['Data Analyst', 'Financial Analyst', 'Research Scientist'],
                'medium': ['Business Analyst', 'Market Researcher', 'Operations Analyst'],
                'low': ['Data Entry Specialist', 'Research Assistant', 'Report Analyst']
            },
            'Collaborative': {
                'high': ['Project Manager', 'Team Lead', 'Consultant'],
                'medium': ['HR Manager', 'Account Manager', 'Community Manager'],
                'low': ['Customer Service', 'Sales Representative', 'Administrative Assistant']
            }
        }

        # Determine performance level
        if performance >= 80:
            level = 'high'
        elif performance >= 60:
            level = 'medium'
        else:
            level = 'low'

        recommendations = {
            'careers': [],
            'skills': [],
            'courses': [],
            'trends': 'Technology and data-driven roles are in high demand',
            'additional_insights': 'Focus on continuous learning and skill development'
        }

        for category in categories[:2]:  # Take top 2 categories
            if category in career_map:
                recommendations['careers'].extend(career_map[category][level][:2])

        # Add relevant skills
        if 'Tech' in categories:
            recommendations['skills'] = ['Programming', 'Problem Solving', 'Data Analysis']
            recommendations['courses'] = ['Python Programming', 'Data Structures', 'Web Development']
        elif 'Creative' in categories:
            recommendations['skills'] = ['Design Thinking', 'Adobe Creative Suite', 'Communication']
            recommendations['courses'] = ['Graphic Design', 'UI/UX Fundamentals', 'Digital Marketing']
        elif 'Analytical' in categories:
            recommendations['skills'] = ['Statistical Analysis', 'Excel', 'Critical Thinking']
            recommendations['courses'] = ['Statistics', 'Data Analytics', 'Business Intelligence']
        else:
            recommendations['skills'] = ['Communication', 'Leadership', 'Team Management']
            recommendations['courses'] = ['Project Management', 'Business Communication', 'Leadership']

        return recommendations


class CourseRecommendationEngine:
    def __init__(self):
        self.course_database = {
            'Tech': {
                'beginner': [
                    'Introduction to Programming',
                    'Web Development Basics',
                    'Computer Science Fundamentals'
                ],
                'intermediate': [
                    'Data Structures and Algorithms',
                    'Database Management',
                    'Full Stack Development'
                ],
                'advanced': [
                    'Machine Learning',
                    'Cloud Computing',
                    'Cybersecurity'
                ]
            },
            'Creative': {
                'beginner': [
                    'Introduction to Design',
                    'Digital Art Basics',
                    'Creative Writing'
                ],
                'intermediate': [
                    'Advanced Graphic Design',
                    'Video Production',
                    'Brand Development'
                ],
                'advanced': [
                    'Motion Graphics',
                    '3D Modeling',
                    'Creative Direction'
                ]
            },
            'Analytical': {
                'beginner': [
                    'Introduction to Statistics',
                    'Business Analytics Basics',
                    'Excel Fundamentals'
                ],
                'intermediate': [
                    'Data Visualization',
                    'Financial Analysis',
                    'Research Methods'
                ],
                'advanced': [
                    'Predictive Analytics',
                    'Advanced Statistics',
                    'Business Intelligence'
                ]
            },
            'Collaborative': {
                'beginner': [
                    'Communication Skills',
                    'Team Building',
                    'Introduction to Management'
                ],
                'intermediate': [
                    'Project Management',
                    'Conflict Resolution',
                    'Leadership Development'
                ],
                'advanced': [
                    'Strategic Management',
                    'Organizational Behavior',
                    'Executive Leadership'
                ]
            }
        }

    def recommend_bridging_courses(self, current_performance: Dict, career_goals: List[str]) -> List[Dict]:
        """
        Recommend bridging courses based on current performance and career goals
        """
        performance_level = self._determine_level(current_performance.get('average_grade', 70))
        categories = current_performance.get('categories', ['Tech'])

        recommendations = []

        for category in categories[:2]:
            if category in self.course_database:
                courses = self.course_database[category][performance_level]
                for course in courses[:2]:
                    recommendations.append({
                        'course_name': course,
                        'category': category,
                        'level': performance_level,
                        'duration': self._estimate_duration(performance_level),
                        'priority': 'High' if category == categories[0] else 'Medium',
                        'skills_gained': self._get_skills_for_course(course)
                    })

        return recommendations

    def _determine_level(self, grade: float) -> str:
        """
        Determine skill level based on grade
        """
        if grade >= 80:
            return 'advanced'
        elif grade >= 60:
            return 'intermediate'
        else:
            return 'beginner'

    def _estimate_duration(self, level: str) -> str:
        """
        Estimate course duration based on level
        """
        durations = {
            'beginner': '4-6 weeks',
            'intermediate': '8-12 weeks',
            'advanced': '12-16 weeks'
        }
        return durations.get(level, '8 weeks')

    def _get_skills_for_course(self, course_name: str) -> List[str]:
        """
        Get skills that will be gained from a course
        """
        skills_map = {
            'Programming': ['Python', 'JavaScript', 'Problem Solving'],
            'Design': ['UI/UX', 'Color Theory', 'Typography'],
            'Analytics': ['Data Analysis', 'Visualization', 'Reporting'],
            'Management': ['Leadership', 'Planning', 'Communication'],
            'Development': ['Coding', 'Testing', 'Debugging'],
            'Statistics': ['Analysis', 'Probability', 'Modeling']
        }

        for keyword, skills in skills_map.items():
            if keyword.lower() in course_name.lower():
                return skills

        return ['Critical Thinking', 'Problem Solving', 'Application']