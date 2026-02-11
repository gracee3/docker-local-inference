INSERT INTO users (role, name, email)
VALUES
    ('parent', 'Sample Parent', 'parent@example.local'),
    ('admin', 'Local Admin', 'admin@example.local')
ON CONFLICT(email) DO NOTHING;

INSERT INTO students (name, grade_level)
SELECT 'Sample Student', '5'
WHERE NOT EXISTS (
    SELECT 1 FROM students WHERE name = 'Sample Student'
);
