var students = require("../controllers/students.js");
var teachers = require("../controllers/teachers.js");
var activities = require("../controllers/activities.js");

module.exports = function(app) {

  // ===================
  // Student API
  // ===================
  app.get('/api/v1/students', function(req, res){
    students.getAllStudents(req, res);
  });

  //This will return all the students for a particular activity id for a given date
  //ID CALL2
  app.get('/api/v1/students/activity', function(req, res){
    students.getAllStudentsByActivityAndDate(req, res);
  });

  //Student info for a particular studentID
  app.get('/api/v1/students/:id', function(req, res){
    students.getStudentById(req, res);
  });

  //Add new student
  app.post('/api/v1/students', function(req, res){
    students.addNewStudent(req, res);
  });

  //Get all the activities for a partictular studentId.
  //Send you a history for the students.
  //ID call1
  app.get('/api/v1/students/:id/activities', function(req, res){
    students.getStudentsActivities(req, res);
  });

  //Bulk upload of the attendance.....
  //ID call3
  //[{STUDENT_ID:, STATUS_ID:, COMMENT:, ACTIVITY_ID:, DATE:}]

  app.post('/api/v1/students/activity', function(req, res){
    students.postStudentAttendance(req, res);
  });

  // ===================
  // Activity API
  // ===================
  app.get('/api/v1/activity', function(req, res){
    activity.getAllActivity(req, res)
  })

  // ===================
  // Teacher API
  // ===================
  app.get('/api/v1/teachers/:email', function(req, res){
    teachers.getTeacherByEmail(req, res);
  });
  app.get('/api/v1/teachers/:id', function(req, res){
    teachers.getTeacherById(req, res);
  });

  app.put('/api/v1/teachers/:id', function(req, res){
    teachers.updateTeacherInfo(req, res);
  });
  app.post('/api/v1/teachers', function(req, res){
    teachers.addNewTeacher(req, res);
  });

  // ===================
  // Activity API
  // ===================
  app.get('/api/v1/activities', function(req, res){
    activities.getAllActivities(req, res);
  });
}
