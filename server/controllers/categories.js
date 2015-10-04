var db = require('../config/database_interface.js')();

module.exports = (function(){
    return {
      getAllCategories : function(req, res){
        var query = db.getAllCategoriesQuery();
        db.query(query, function(result){
          res.status(200).json(result);
        });
      }
    }
  })();
