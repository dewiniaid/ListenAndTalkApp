var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllActivity : function(req, res){
        var query = db.getAllActivitiesQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getAllDetailActivity : function(req, res){
        var query = db.getAllDetailActivityQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      addActivity : function(req, res){
        var query = db.addActivityQuery(
          req.body.name,
          req.body.staff_id,
          req.body.category_id,
          req.body.location_id,
          req.body.allow_dropins || false,
          req.body.start_date,
          req.body.end_date
        );
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
  })();
