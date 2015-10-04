var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllActivity : function(req, res){
        var query = db.getAllActivityQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
  })();
