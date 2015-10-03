var test = require("../server/controllers/cTest.js");
var students = require("../server/controllers/students.js");

module.exports = function(app) {
  app.get('/api/test', function(req, res) {
    test.test(req, res);
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
};
