import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os
from datetime import datetime, timedelta
from django.conf import settings

class PerformancePredictionModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'performance_model.pkl')
        self.scaler_path = os.path.join(settings.BASE_DIR, 'ml_models', 'scaler.pkl')

    def prepare_features(self, student_data):
        """
        Prepare features for the ML model
        """
        features = {
            'attendance_rate': student_data.get('attendance_rate', 0),
            'test_average': student_data.get('test_average', 0),
            'assignments_completed': student_data.get('assignments_completed', 0),
            'participation_score': student_data.get('participation_score', 0),
            'previous_grade': student_data.get('previous_grade', 0),
            'study_hours': student_data.get('study_hours', 0),
            'quiz_scores': student_data.get('quiz_scores', 0),
        }
        return pd.DataFrame([features])

    def train_model(self, training_data):
        """
        Train the performance prediction model
        """
        X = training_data.drop(['actual_grade'], axis=1)
        y = training_data['actual_grade']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train ensemble model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate model
        predictions = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, predictions)
        r2 = r2_score(y_test, predictions)

        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)

        return {'mae': mae, 'r2': r2}

    def predict_performance(self, student_data):
        """
        Predict student performance
        """
        if not self.model:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
            else:
                # Use default model if not trained
                self.model = LinearRegression()
                return self._default_prediction(student_data)

        features = self.prepare_features(student_data)
        features_scaled = self.scaler.transform(features)
        prediction = self.model.predict(features_scaled)[0]

        # Ensure prediction is within valid range
        prediction = max(0, min(100, prediction))

        return {
            'predicted_grade': round(prediction, 2),
            'confidence': self._calculate_confidence(student_data),
            'trend': self._analyze_trend(student_data)
        }

    def _default_prediction(self, student_data):
        """
        Default prediction when model is not available
        """
        base_score = 70
        attendance_weight = 0.3
        test_weight = 0.4
        participation_weight = 0.3

        predicted = (
            base_score +
            (student_data.get('attendance_rate', 75) - 75) * attendance_weight +
            (student_data.get('test_average', 70) - 70) * test_weight +
            (student_data.get('participation_score', 70) - 70) * participation_weight
        )

        return {
            'predicted_grade': round(max(0, min(100, predicted)), 2),
            'confidence': 'Medium',
            'trend': 'Stable'
        }

    def _calculate_confidence(self, student_data):
        """
        Calculate confidence level of prediction
        """
        data_completeness = sum([
            1 for key in ['attendance_rate', 'test_average', 'assignments_completed']
            if key in student_data and student_data[key] is not None
        ]) / 7

        if data_completeness > 0.8:
            return 'High'
        elif data_completeness > 0.5:
            return 'Medium'
        else:
            return 'Low'

    def _analyze_trend(self, student_data):
        """
        Analyze performance trend
        """
        current = student_data.get('test_average', 0)
        previous = student_data.get('previous_grade', 0)

        if current - previous > 5:
            return 'Improving'
        elif previous - current > 5:
            return 'Declining'
        else:
            return 'Stable'


class ImprovementStrategyGenerator:
    def __init__(self):
        self.strategies = {
            'low_attendance': [
                "Set daily reminders for classes",
                "Create a consistent morning routine",
                "Find a study buddy for accountability",
                "Review missed class materials within 24 hours"
            ],
            'low_test_scores': [
                "Practice with past exam papers",
                "Create comprehensive study notes",
                "Join or form a study group",
                "Schedule regular review sessions",
                "Use active recall techniques"
            ],
            'low_participation': [
                "Prepare questions before each class",
                "Set a goal to contribute once per class",
                "Review materials before class",
                "Practice speaking in smaller groups first"
            ],
            'low_assignments': [
                "Break assignments into smaller tasks",
                "Use a planner to track deadlines",
                "Start assignments early to avoid rush",
                "Seek help from teachers when stuck"
            ]
        }

    def generate_strategies(self, student_data, prediction_result):
        """
        Generate personalized improvement strategies
        """
        strategies = []
        priority_areas = []

        # Analyze weak areas
        if student_data.get('attendance_rate', 100) < 75:
            priority_areas.append('attendance')
            strategies.extend(self.strategies['low_attendance'])

        if student_data.get('test_average', 100) < 60:
            priority_areas.append('test_scores')
            strategies.extend(self.strategies['low_test_scores'])

        if student_data.get('participation_score', 100) < 50:
            priority_areas.append('participation')
            strategies.extend(self.strategies['low_participation'])

        if student_data.get('assignments_completed', 100) < 80:
            priority_areas.append('assignments')
            strategies.extend(self.strategies['low_assignments'])

        # Add general strategies based on predicted grade
        predicted_grade = prediction_result.get('predicted_grade', 70)

        if predicted_grade < 50:
            strategies.append("Consider scheduling tutoring sessions")
            strategies.append("Meet with academic advisor weekly")
        elif predicted_grade < 70:
            strategies.append("Dedicate 2 extra hours daily for focused study")
            strategies.append("Review and revise notes after each class")
        else:
            strategies.append("Maintain current study habits")
            strategies.append("Challenge yourself with advanced materials")

        return {
            'priority_areas': priority_areas,
            'strategies': strategies[:6],  # Return top 6 strategies
            'estimated_improvement': self._estimate_improvement(priority_areas),
            'timeline': self._suggest_timeline(priority_areas)
        }

    def _estimate_improvement(self, priority_areas):
        """
        Estimate potential grade improvement
        """
        improvement_potential = {
            'attendance': 10,
            'test_scores': 15,
            'participation': 8,
            'assignments': 12
        }

        total_improvement = sum([
            improvement_potential.get(area, 0)
            for area in priority_areas
        ])

        return min(total_improvement, 25)  # Cap at 25% improvement

    def _suggest_timeline(self, priority_areas):
        """
        Suggest timeline for improvement
        """
        if len(priority_areas) >= 3:
            return "3-4 months for significant improvement"
        elif len(priority_areas) == 2:
            return "2-3 months for noticeable improvement"
        elif len(priority_areas) == 1:
            return "4-6 weeks for targeted improvement"
        else:
            return "Maintain current performance"