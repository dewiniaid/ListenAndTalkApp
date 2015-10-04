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
        var deactivate = req.query.deactivate;
        var query = db.dectivateStudentQuery(id, deactivate.toLowerCase() === 'true');
        console.log(query);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      getAllStudentsByActivityAndDate : function(req, res){
        var activityId = req.query.activityId;
        var date = req.query.date;
        var query = db.getAllStudentsByActivityAndDateQuery(activityId, date);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },

      /*
      {
      "data" : [{"STUDENT_ID":"2", "STATUS_ID":"1", "COMMENT":"HHAHA", "ACTIVITY_ID":"4", "DATE":"2015-10-01"}]
      }*/
      postStudentAttendance : function(req, res){
        if(req.is('application/json')){
          var data = req.body.data
          for (var i = 0; i < data.length; i++) {
            var item = req.body.data[i]
            //activityId, studentId, date, statusId, comment
            var query = db.postStudentAttendance(item.ACTIVITY_ID, item.STUDENT_ID, item.DATE, item.STATUS_ID, item.COMMENT);
            db.query(query, function(result){
            });
          }
          res.status(200).json(req.body.data);
        }else{
          res.status(400).send('Bad Request');
        }
      },

      addNewStudent : function(req, res){
        var firstName = res.params.firstName;
        var lastName = res.params.lastName;
        var query = db.addNewStudentQuery(firstName, lastName);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
})();
