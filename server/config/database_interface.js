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
      //TODO THIS QUERY
      return {
          text: "SELECT * FROM " + TEACHER_TABLE + " WHERE email = $1",
          values: [email],
          name: 'teacherEmail'
      };
    },

    addNewStudentQuery : function(firstName, lastName){
      //TODO THIS QUERY
      return {
          text: "",
          values: [firstName, lastName],
          name: 'adding new student by name'
      };
    }


  };
};
