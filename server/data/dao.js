

module.exports = (function(){
	var pg = require('pg');
	// var connectionString = process.env.DATABASE_URL
	var hostname = 'listenandtalk.cloudapp.net'
	var port = 5432;
	var database = 'postgres';
	var schema = 'listenandtalk,public';
	var username = 'backend';
	var password = 'BNC8HYC2xIKmHsEDBmNx';

	var connectionString = "postgres://backend:BNC8HYC2xIKmHsEDBmNx@listenandtalk.cloudapp.net:5432/postgres";

	// var connectionString = process.env.LISTEN_AND_TALK_DATABASE_URL;


	var client = new pg.Client(connectionString);
	client.connect();
	var SET_SEARCH_PATH_QUERY = "SET SEARCH_PATH = " + schema;
	client.query(SET_SEARCH_PATH_QUERY);


	var STUDENT_TABLE = "student";
	var TEACHER_TABLE = "staff";
	var LOCATION_TABLE = "location";
	var ATTENDANCE_STATUS_TABLE = "attendance_status";
	var ACTIVITY_TABLE = "activity";
	var ACTIVITY_ENROLLMENT_TABLE = "activity_enrollment";
	var ATTENDANCE_TABLE = "attendance";


	function doQuery(inputQuery){
		console.log("doQuery");
		var query = client.query(inputQuery);
		var results = [];
		query.on('row', function(row) {
			console.log("adding another row");
	        results.push(row);
	    });

	    // After all data is returned, close connection and return results
	    query.on('end', function() {
	    	console.log(results);
	    	return results;
		});

	}

	return {
		getAllStudents : function () {
			console.log("Query: getAllStudents");
			var studentQuery = "SELECT * FROM " + STUDENT_TABLE;
			return doQuery(studentQuery);
		},

		getStudentById : function(id) {
			console.log("Query: getStudentById");
			// var studentQuery = "SELECT * FROM " + STUDENT_TABLE + " WHERE id = $1";
			var studentQuery = {
      			text: "SELECT * FROM " + STUDENT_TABLE + " WHERE id = $1",
			    values: [id],
			    name: 'studentId'
			};
			return doQuery(studentQuery);
		},

		getTeacherByEmail : function(email){
			console.log("Query: getTeacherByEmail");
			var teacherQuery = {
      			text: "SELECT * FROM " + TEACHER_TABLE + " WHERE email = $1",
			    values: [email],
			    name: 'teacherEmail'
			};
			return doQuery(teacherQuery);
		},

		getAllTeachers : function(email){
			console.log("Query: getTeacherByEmail");
			var teacherQuery = "SELECT * FROM " + TEACHER_TABLE;
			return doQuery(teacherQuery);
		}

	}
})();
