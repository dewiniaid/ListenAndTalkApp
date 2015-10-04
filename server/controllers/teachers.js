var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getTeachers : function(req, res) {
        var email = req.params.email;
        var query = db.getTeachersQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getTeacherByEmail : function(req, res) {
        var email = req.params.email;
        var query = db.getTeacherByEmailQuery(email);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getTeacherInfo : function(req, res){
        var query = db.getAllTeachersQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      updateTeacherInfo : function(req, res){
        var id = req.params.id;
        var deactivate = req.query.deactivate;
        var query = db.dectivateTeacherQuery(id, deactivate.toLowerCase() === 'true');
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getActivityByTeacherEmail : function(req, res){
        var email = req.params.email;
        var query = db.getActivityByTeacherEmailQuery(email);
        console.log(query);
        db.query(query, function(result){
          console.log(result);
          res.status(200).json(result);
        });
      }
    }
})();
