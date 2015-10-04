var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllStatus : function(req, res){
        var query = db.getAllStatusQuery();
        console.log(query);
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
  })();
