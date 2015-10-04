var config = require("./config.js");
var pg = require('pg');


  var STUDENT_TABLE = "student";
  var TEACHER_TABLE = "staff";
  var LOCATION_TABLE = "location";
  var ATTENDANCE_STATUS_TABLE = "attendance_status";
  var ACTIVITY_TABLE = "activity";
  var ACTIVITY_ENROLLMENT_TABLE = "activity_enrollment";
  var ATTENDANCE_TABLE = "attendance";


var AddUpdateGenerator = function(table, keyfields, valuefields) {
    /* Creates queries and API wrappers for add/update functionality for objects that are edited/updated
     * table: Table to work with..
     * keyfields: List of fields that identify primary key components.  Ignored on insertions, used for WHERE on updates.
     * valuefields: List of fields that identify values that are inserted/updated.
     */

    this.keyfields = keyfields;
    this.valuefields = valuefields;
    this.table = table;

    function generateParams(ct) {
        var ret = '';
        for (var i = 1; i <= ct; ++i) {
            if (i != 1) ret += ', ';  // Add comma first if this isn't the first param
            ret += '$' + i;
        }
        return ret;
    }

    var paramNum = 1; // Dynamic query parameter generation

    var updateSql = "UPDATE " + this.table + " SET ";
    for (var idx = 0; idx < this.valuefields.length; ++idx) {
        if (idx) updateSql += ", ";
        updateSql += this.valuefields[idx] + "=$" + (paramNum++);
    }
    updateSql += " WHERE ";
    for (var idx = 0; idx < this.keyfields.length; ++idx) {
        updateSql += this.keyfields[idx] += "=$" + (paramNum++);
    }
	updateSql += " RETURNING *";
    this.updateSql = updateSql;

    paramNum = 1; // reset count for new query
    var insertSql = "INSERT INTO " + table + "(" + this.valuefields.join(", ") + ") VALUES (";
    for (var idx = 0; idx < this.valuefields.length; ++idx) {
        if (idx) insertSql += ", ";
        insertSql += "$" + (paramNum++);
    }
    insertSql += ") RETURNING *";
    this.insertSql = insertSql;

    return this;
}

AddUpdateGenerator.prototype.generateInsertQuery = function () {
    var _t = this;
    return function() {
        return {
            text: _t.insertSql,
            values: arguments,
            name: _t.table + "_autogen_insert_query"
        }
    };
};

AddUpdateGenerator.prototype.generateUpdateQuery = function () {
    var _t = this;
    return function() {
        return {
            text: _t.updateSql,
            values: arguments,
            name: _t.table + "_autogen_update_query"
        }
    };
};


var StudentUpdater = new AddUpdateGenerator('student', ['id'], ['name_first', 'name_last']);
var StaffUpdater = new AddUpdateGenerator('staff', ['id'], ['name_first', 'name_last', 'email']);


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
      return {
          text: "INSERT INTO attendance_upsert (activity_id, student_id, date, status_id, comment, date_entered) VALUES ($1, $2, $3, $4, $5, 'now')",
          values: [activityId, studentId, date, statusId, comment],
          name: 'Posting student attendance'
      };
    },

/*
    addNewStudentQuery : function(firstName, lastName){
      return {
          text: "INSERT INTO "+ STUDENT_TABLE +"(name_first, name_last) VALUES ($1, $2)",
          values: [firstName, lastName],
          name: 'adding new student by name'
      };
    },
*/	
	addNewStudentQuery : StudentUpdater.generateInsertQuery(),
	updateStudentQuery : StudentUpdater.generateUpdateQuery(),

    removeStudentQuery : function(id) {
      return {
          text: "DELETE FROM "+ STUDENT_TABLE +" WHERE id = $1",
          values: [id],
          name: 'remove student by id'
      };
    },
/*
    addNewTeacherQuery : function(firstName, lastName, email){
      return {
          text: "INSERT INTO "+ TEACHER_TABLE +"(name_first, name_last, email) VALUES ($1, $2, $3)",
          values: [firstName, lastName, email],
          name: 'adding new student by name'
      };
    },
*/
	addNewTeacherQuery : StaffUpdater.generateInsertQuery(),
	updateTeacherQuery : StaffUpdater.generateUpdateQuery(),

    removeTeacherQuery : function(id){
      return {
          text: "DELETE FROM "+ TEACHER_TABLE +" WHERE id = $1",
          values: [id],
          name: 'remove staff by id'
      };
    },

    getAllActivitiesQuery : function() {
      return "SELECT * from "+ ACTIVITY_TABLE;
    },

    getAllStatusQuery : function(){
      return "SELECT * from "+ ATTENDANCE_STATUS_TABLE;
    },

    getTeachersQuery : function(){
      return "SELECT * from "+ TEACHER_TABLE;
    },

    dectivateStudentQuery : function(id, deactivate){
      if(deactivate){
        return {
            text: "UPDATE "+ STUDENT_TABLE + " SET date_inactive = now() WHERE id = $1",
            values: [id],
            name: 'id'
        };
      }else{
        return {
            text: "UPDATE "+ STUDENT_TABLE + " SET date_inactive = null WHERE id = $1",
            values: [id],
            name: 'id'
        };
      }
    },

    dectivateTeacherQuery : function(id, deactivate){
      if(deactivate){
        return {
            text: "UPDATE "+ TEACHER_TABLE + " SET date_inactive = now() WHERE id = $1",
            values: [id],
            name: 'id'
        };
      }else{
        return {
            text: "UPDATE "+ TEACHER_TABLE + " SET date_inactive = null WHERE id = $1",
            values: [id],
            name: 'id'
        };
      }
    },

    getStudentHistoryQuery : function(id){
      return {
          text: "SELECT * from " + ATTENDANCE_TABLE +" WHERE student_id = $1",
          values: [id]
      };
    },

    getStudentHistoryQueryByDate : function(id, startDate, endDate){
      return {
          text: "SELECT * from " + ATTENDANCE_TABLE +" WHERE student_id = $1 and date_entered between $2 and $3",
          values: [id, startDate, endDate]
      };
    },

    getActivityByTeacherEmailQuery : function(email){
      return {
          text: "SELECT * FROM " + ACTIVITY_TABLE +" WHERE staff_id = (SELECT id FROM " + TEACHER_TABLE + " WHERE email = $1)",
          values: [email],
          name: 'teacherEmail'
      };
    }
  };
};
