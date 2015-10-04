var config = require("./config.js");
var pg = require('pg');


  var STUDENT_TABLE = "student";
  var TEACHER_TABLE = "staff";
  var LOCATION_TABLE = "location";
  var ATTENDANCE_STATUS_TABLE = "attendance_status";
  var ACTIVITY_TABLE = "activity";
  var ACTIVITY_ENROLLMENT_TABLE = "activity_enrollment";
  var ATTENDANCE_TABLE = "attendance";

module.exports = function() {
  return {
    query : function(inputQuery, callback){
			pg.connect(config.connection, function(err, client, done){
				var results = [];
				client.query("SET SEARCH_PATH = " + config.schema);
				var query = client.query(inputQuery);

				// Stream results back one row at a time
        query.on('row', function(row) {
            results.push(row);
        });

        query.on('end', function() {
            client.end();
            callback(results);
        });

        // Handle Errors
        if(err) {
          console.log(err);
        }
			});
		},
    getStudentByIdQuery : function(id){
      return {
          text: "SELECT * FROM " + STUDENT_TABLE + " WHERE id = $1",
          values: [id],
          name: 'studentId'
      };
    },

    getAllStudentsQuery : function(){
        return "SELECT * FROM student ORDER BY id ASC";
    },

    getTeacherByEmailQuery : function(email){
      return {
          text: "SELECT * FROM " + TEACHER_TABLE + " WHERE email = $1",
          values: [email],
          name: 'teacherEmail'
      };
    },


    // getTeacherById : function(id){
    //   return {
    //       text: "SELECT * FROM " + TEACHER_TABLE + " WHERE id = $1",
    //       values: [id],
    //       name: 'teacherId'
    //   };
    // },

    getAllTeachersQuery : function(){
      return "SELECT * FROM " + TEACHER_TABLE;
    },

    getAllStudentsByActivityAndDateQuery : function(activityId, date){

      return {
        text:"SELECT t.* FROM (\
              (\
              SELECT\
              	 student.id AS student_id\
              	,student.name_first\
              	,student.name_last\
              	,activity.id AS activity_id\
              	,a.date_entered\
              	,a.status_id\
              	,a.comment\
              FROM\
              	activity_enrollment AS ae\
              	INNER JOIN student ON ae.student_id=student.id\
              	INNER JOIN activity ON ae.activity_id=activity.id\
              	LEFT JOIN attendance AS a ON a.student_id=student.id AND a.activity_id=activity.id AND a.date=$1\
              WHERE\
              	$1 BETWEEN activity.start_date AND activity.end_date\
              	AND $1 BETWEEN ae.start_date AND COALESCE(ae.end_date, 'infinity')\
              	AND activity.id=$2\
              )\
              UNION DISTINCT\
              (\
              SELECT \
              	 student.id AS student_id\
              	,student.name_first\
              	,student.name_last\
              	,activity.id AS activity_id\
              	,a.date_entered\
              	,a.status_id\
              	,a.comment\
              FROM\
              	attendance AS a \
              	INNER JOIN student ON student.id=a.student_id\
              	INNER JOIN activity ON activity.id=a.activity_id\
              WHERE\
              	a.date=$1\
              	AND activity.id=$2\
              )\
              ) AS t\
              ORDER BY t.name_first,t.name_last;",
              values: [date, activityId]
            };
    },


    postStudentAttendance : function(activityId, studentId, date, statusId, comment){
      //TODO THIS QUERY
      return {
          text: "INSERT INTO attendance_upsert (activity_id, student_id, date, status_id, comment, date_entered) VALUES ($1, $2, $3, $4, $5, 'now')",
          values: [activityId, studentId, date, statusId, comment],
          name: 'Posting student attendance'
      };
    },

    addNewStudentQuery : function(firstName, lastName){
      //TODO THIS QUERY
      return {
          text: "",
          values: [firstName, lastName],
          name: 'adding new student by name'
      };
    },

    getAllActivityQuery : function(){
      return "SELECT * from "+ ACTIVITY_TABLE;
    },

    getAllStatusQuery : function(){
      return "SELECT * from "+ ATTENDANCE_STATUS_TABLE;
    },

    getTeachersQuery : function(){
      return "SELECT * from "+ TEACHER_TABLE;
    },

    getActivityByTeacherEmailQuery : function(email){
      return {
          text: "SELECT * FROM "+ACTIVITY_TABLE +" WHERE staff_id = (SELECT id FROM " + TEACHER_TABLE + " WHERE email = $1)",
          values: [email],
          name: 'teacherEmail'
      };
    }

  };
};
