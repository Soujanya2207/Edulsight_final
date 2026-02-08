# Automatic Course Suggestion System

## Overview
The system now automatically generates course suggestions based on teacher-provided grades and attendance data.

## How It Works

### 1. Automatic Triggers
Course suggestions are automatically generated when teachers:
- Add attendance records
- Add test scores
- Add grades

### 2. Suggestion Criteria

#### Critical Priority (Red Alert)
- **Attendance < 50%**: Time Management & Attendance Improvement Program
- **Average Grade < 40%**: Foundation Strengthening Course
- **Subject Grade < 50%**: Subject-specific Remedial Program

#### High Priority (Orange Alert)
- **Attendance 50-75%**: Time Management & Attendance Improvement Program
- **Average Grade 40-60%**: Foundation Strengthening Course

#### Low Priority (Blue - Optional)
- **Average Grade > 85%**: Advanced Placement Program (for high performers)

### 3. Key Features

- **No Duplicate Suggestions**: System checks for existing suggestions in the last 7 days before creating new ones
- **Automatic Notifications**: Students receive notifications when new suggestions are generated
- **Performance-Based**: All suggestions include current performance metrics (attendance %, grade %)
- **Target Goals**: Each suggestion includes specific improvement targets
- **Subject-Specific**: Poor performance in individual subjects triggers targeted remedial programs

### 4. Data Flow

1. Teacher enters data (attendance/grades/tests)
2. System calculates performance metrics
3. Auto-generates appropriate course suggestions
4. Sends notification to student
5. Student can view and accept/decline suggestions

### 5. Student View

Students can:
- View all course suggestions at `/student/course-suggestions/`
- See suggestions categorized by priority
- Accept or decline suggestions
- Provide feedback on suggestions
- Track which courses they've accepted

### 6. Teacher Benefits

- No manual intervention needed for basic suggestions
- Automatic tracking of student performance issues
- Consistent suggestion criteria across all students
- Can still manually add custom course suggestions when needed

## Implementation Details

### Functions Added:
- `auto_generate_course_suggestions()` in `views.py`
- Integrated into:
  - `manage_attendance()` - triggers on attendance marking
  - `manage_tests()` - triggers on test score entry
  - `teacher_grade_management()` - triggers on grade entry

### Models Used:
- `CourseSuggestion` - stores all suggestions
- `Notification` - alerts students
- `Grade`, `Attendance`, `WeeklyTest` - source data

### Thresholds:
- Critical: <50% attendance or <40% grades
- High: 50-75% attendance or 40-60% grades
- Subject-specific: <50% in any subject
- Advanced: >85% overall performance