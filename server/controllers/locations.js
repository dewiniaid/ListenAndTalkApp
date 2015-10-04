var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllLocations : function(req, res){
        var query = db.getAllLocationsQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
  })();
