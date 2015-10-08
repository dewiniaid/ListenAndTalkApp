INSERT INTO staff (name_first, name_last,email)
VALUES ('Kevin', 'OBrien', 'kevin.obrien@praece.com');

INSERT INTO attendance_status (name)
VALUES
	('Present'), 
	('Absent'),
	('Absent - Excused') -- ,
	-- ('Not Expected')
RETURNING *;
