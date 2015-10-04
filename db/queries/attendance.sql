SET search_path=listenandtalk,public;

-- Reference for some queries.


SELECT t.* FROM (

-- Retrieve students who are rostered for a single date OR have attendance for that single date.
(
SELECT 
	-- t.date, student.*, activity.*, a.*
	 student.id AS student_id
	,student.name_first
	,student.name_last
	,activity.id AS activity_id
	,a.date_entered
	,a.status_id
	,a.comment
FROM
	activity_enrollment AS ae
	INNER JOIN student ON ae.student_id=student.id
	INNER JOIN activity ON ae.activity_id=activity.id
	LEFT JOIN attendance AS a ON a.student_id=student.id AND a.activity_id=activity.id AND a.date='2015-10-01'
WHERE
	'2015-10-01' BETWEEN activity.start_date AND activity.end_date
	AND '2015-10-01' BETWEEN ae.start_date AND COALESCE(ae.end_date, 'infinity')
	AND activity.id=1
)
UNION DISTINCT
(
SELECT 
	-- t.date, student.*, activity.*, a.*
	 student.id AS student_id
	,student.name_first
	,student.name_last
	,activity.id AS activity_id
	,a.date_entered
	,a.status_id
	,a.comment
FROM
	attendance AS a 
	INNER JOIN student ON student.id=a.student_id
	INNER JOIN activity ON activity.id=a.activity_id
WHERE
	a.date='2015-10-01'
	AND activity.id=1
)

) AS t
ORDER BY t.name_first, t.name_last;




-- Skeleton for reporting attendance (only uses entries that exist)
SELECT
	s.id AS student_id, s.name_first AS student_name_first, s.name_last AS student_name_last,
	t.id AS staff_id, t.name_first AS staff_name_first, t.name_last AS staff_name_last,
	
	act.id AS activity_id, act.name AS activity_name, cat.id AS category_id, cat.name AS category_name,
	
	a.date, a.date_entered, a.status_id, a.comment, status.name AS status_name

FROM
	attendance AS a
	LEFT JOIN attendance_status AS status ON a.status_id=status.id
	INNER JOIN activity AS act ON act.id=a.activity_id
		INNER JOIN staff AS t ON act.staff_id=t.id
		INNER JOIN category AS cat ON cat.id=act.category_id
	INNER JOIN student AS s ON a.student_id=s.id
--
-- WHERE
--	staff.id=$1
--	activity.id=$1
--	cat.id=$1
--	a.date BETWEEN $1 AND $2
--

SELECT * FROM attendance;
