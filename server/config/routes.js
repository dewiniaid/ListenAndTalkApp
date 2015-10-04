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

  app.get('/api/v1/students/activity', function(req, res){
    students.getAllStudentsByActivityAndDate(req, res);
  });

  app.get('/api/v1/students/:id', function(req, res){
    students.getStudentById(req, res);
  });
  app.put('/api/v1/students/:id', function(req, res){
    students.putStudentById(req, res);
  });
  app.post('/api/v1/students', function(req, res){
    students.addNewStudent(req, res);
  });
  app.get('/api/v1/students/:id/activities', function(req, res){
    students.getStudentsActivities(req, res);
  });

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
};
