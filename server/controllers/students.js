var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllStudents : function(req, res){
        var query = db.getAllStudentsQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getStudentById : function(req, res){
        var id = req.params.id;
        var query = db.getStudentByIdQuery(id);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      putStudentById : function(req, res){
        var id = req.params.id;
        var query = db.putStudentByIdQuery(id);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      getAllStudentsByActivityAndDate : function(req, res){
        var activityId = req.params.activityId;
        var date = req.params.date;
        var query = db.getAllStudentsByActivityAndDateQuery(activityId, date);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      addNewStudent : function(req, res){
        var firstName = res.params.firstName;
        var lastName = res.params.lastName;
        var query = db.addNewStudentQuery(firstName, lastName);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

    }
})();
