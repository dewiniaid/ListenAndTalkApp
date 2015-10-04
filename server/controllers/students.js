var postgres = require('../config/postgres.js')();

module.exports = (function(){
    return {
      getAllStudents : function(req, res){
        var query = "SELECT * FROM student ORDER BY id ASC";
        postgres.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getStudentById : function(req, res){
        var query = "SELECT * FROM student WHERE id = " + req.params.id;
        postgres.query(query, function(result){
          res.status(200).json(result);
        });
      },
      putStudentById : function(req, res){
        res.status(200).send("Student are put on this endpoint");
      },
      addNewStudent : function(req, res){
        res.status(200).send("Student are added on this endpoint");
      },
      getStudentsActivities : function(req, res){
        res.status(200).send("Find students by activities");
      }
    }
})();
