var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getTeacherByEmail : function(req, res) {
        var email = req.params.email;
        var query = db.getTeacherByEmailQuery(email);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      // getTeacherById : function(req, res){
      //   var staffId = req.params.id;
      //   var query = db.getTeacherByIdQuery(staffId);
      //   db.query(query, function(result){
      //     res.status(200).json(result);
      //   });
      // },
      getTeacherInfo : function(req, res){
        var query = db.getAllTeachersQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      updateTeacherInfo : function(req, res){
        res.status(200).send("Teacher are updated on this endpoint");
      },
      addNewTeacher : function(req, res){
        res.status(200).send("Teacher are added on this endpoint");
      }
    }
})();
