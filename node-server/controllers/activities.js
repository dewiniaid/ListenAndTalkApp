var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllActivities : function(req, res) {
        var query = db.getAllActivitiesQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
})();
