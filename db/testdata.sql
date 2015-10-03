SET search_path=listenandtalk,public;

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

UPDATE student SET date_deleted='now' WHERE name_first='Deleted';



INSERT INTO teacher (name_first, name_last) 
VALUES 
	('Kevin', 'OBrien'),
	('Suzanne', 'Quigley'),
	('Erik', 'Kramer'),
	('Deleted', 'Teacher')
RETURNING *;

UPDATE teacher SET date_deleted='now' WHERE name_first='Deleted';

-- Attendance statuses.
-- Probably production data too.
INSERT INTO attendance_status (name)
VALUES
	('Present'), 
	('Absent'),
	('Excused'),
	('Not Expected')
;

-- Rest of this is waiting on finalizing the course/location/roster/whatever paradigm.
