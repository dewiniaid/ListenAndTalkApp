var test = require("../controllers/cTest.js");
var students = require("../controllers/students.js");
var teachers = require("../controllers/teachers.js");

module.exports = function(app) {
  // GET /api/test
  app.get('/api/test', function(req, res) {
    test.test(req, res);
  });
  // GET api/test_params/1
  app.get('/api/test_params/:id', function(req, res) {
    test.test_params(req, res);
  });
  // POST api/test_post
  app.post('/api/test_post', function(req, res) {
    test.test_post(req, res);
  });

  app.get('/api/v1/students', function(req, res){
    students.getAllStudents(req, res);
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
  app.get('/api/v1/teachers/:id', function(req, res){
    teachers.getTeacherInfo(req, res);
  });
  app.put('/api/v1/teachers/:id', function(req, res){
    teachers.updateTeacherInfo(req, res);
  });
  app.post('/api/v1/teachers', function(req, res){
    teachers.addNewTeacher(req, res);
  });
};
