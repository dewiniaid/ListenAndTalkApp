BEGIN;
SET search_path=listenandtalk,public;

-- Attendance statuses.
-- Probably production data too.
INSERT INTO attendance_status (name)
VALUES
	('Present'), 
	('Absent'),
	('Absent - Excused') -- ,
	-- ('Not Expected')
RETURNING *;
;

-- Activity categories
INSERT INTO category (name) 
VALUES 
	('Class'),
	('Therapy'),
	('Extra-Curricular')
RETURNING *;



INSERT INTO student (name_first, name_last)
VALUES 
	('Sean', 'Caldwell'),
	('Kelsey', 'Davis'),
	('Chris', 'Tran'),
	('Jack', 'Chang'),
	('Dylan', 'Sena'),
	('Mark', 'Geronimo'),
	('Daniel', 'Grace'),
	('Rahul', 'Mehan'),
	('Mihir', 'Shan'),
	('Brian', 'Finck'),
	('Edward', 'Byers'),
	('Kirsten', 'Grace'),
	('Deleted', 'Student')
RETURNING *;

UPDATE student SET date_inactive='now' WHERE name_first='Deleted';



INSERT INTO staff (name_first, name_last) 
VALUES 
	('Kevin', 'OBrien'),
	('Suzanne', 'Quigley'),
	('Erik', 'Kramer'),
	('Deleted', 'Teacher')
RETURNING *;

UPDATE staff SET date_inactive='now' WHERE name_first='Deleted';
UPDATE staff SET email='staff' || id || '@example.com' WHERE email IS NULL;



INSERT INTO location (name) 
SELECT name_first || E'\'s Room' FROM staff
RETURNING *;



INSERT INTO activity (name, staff_id, location_id, category_id, start_date, end_date)
SELECT 
	t.name_first || E'\'s Class',
	t.id,
	(SELECT id FROM location WHERE name=(t.name_first || E'\'s Room')), --'
	(SELECT id FROM category WHERE name='Class'),
	NOW() - '60 days'::interval,
	NOW() + '60 days'::interval
FROM
	staff AS t
RETURNING *;



INSERT INTO activity_enrollment (activity_id, student_id, start_date, end_date)
SELECT a.id, s.id, '-infinity', CASE WHEN ((a.id+s.id)%10)::BOOLEAN THEN NULL::date ELSE 'now'::date END
FROM activity AS a INNER JOIN student AS s ON ((a.id+s.id)%3 = 0);

SELECT COUNT(DISTINCT student_id) FROM activity_enrollment;
SELECT * FROM activity_enrollment ORDER BY student_id;
COMMIT;

