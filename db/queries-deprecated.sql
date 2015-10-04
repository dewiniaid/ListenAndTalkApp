SET search_path=listenandtalk,public;

-- Reference for some queries.

-- Retrieve students who are rostered for a single date OR have attendance for that single date.
(
SELECT 
	-- t.date, student.*, activity.*, a.*
	student.id AS student_id, activity.id AS activity_id, a.date_entered, a.status_id, a.comment
FROM
	activity_enrollment AS ae
	INNER JOIN student ON ae.student_id=student.id
	INNER JOIN activity ON ae.activity_id=activity.id
	LEFT JOIN attendance AS a ON a.student_id=student.id AND a.activity_id=activity.id AND a.date='2015-10-01'
WHERE
	'2015-10-01' BETWEEN activity.start_date AND activity.end_date
	AND '2015-10-01' BETWEEN ae.start_date AND COALESCE(ae.end_date, 'infinity')
)
UNION DISTINCT
(
SELECT
	-- a.date, student.*, activity.*, a.*
	student.id AS student_id, activity.id AS activity_id, a.date_entered, a.status_id, a.comment

FROM
	attendance AS a 
	INNER JOIN student ON student.id=a.student_id
	INNER JOIN activity ON activity.id=a.activity_id
WHERE
	a.date='2015-10-01'
);



-- Retrieve students who are either rostered for a range of dates OR have attendance entered for the same dates.
(
SELECT 
	-- t.date, student.*, activity.*, a.*
	t.date, student.id AS student_id, activity.id AS activity_id, a.date_entered, a.status_id, a.comment
FROM
	(
		SELECT DISTINCT s.id AS student_id, a.id AS activity_id, t.date::date AS date
		FROM
			activity_enrollment AS ae
			INNER JOIN student AS s ON ae.student_id=s.id
			INNER JOIN activity AS a ON ae.activity_id=a.id
			INNER JOIN generate_series('2015-10-01'::date, '2015-11-01'::date, '1 day'::interval) AS t(date) ON t.date::date BETWEEN GREATEST(ae.start_date, a.start_date) AND LEAST(ae.end_date, a.end_date)
	) AS t
	INNER JOIN student ON student.id=t.student_id
	INNER JOIN activity ON activity.id=t.activity_id
	LEFT JOIN attendance AS a ON a.student_id=t.student_id AND a.activity_id=t.activity_id AND a.date=t.date
)
UNION DISTINCT
(
SELECT
	-- a.date, student.*, activity.*, a.*
	a.date, student.id AS student_id, activity.id AS activity_id, a.date_entered, a.status_id, a.comment

FROM
	attendance AS a 
	INNER JOIN student ON student.id=a.student_id
	INNER JOIN activity ON activity.id=a.activity_id
WHERE
	a.date BETWEEN '2015-10-01'::date AND '2015-11-01'::date
)
;


