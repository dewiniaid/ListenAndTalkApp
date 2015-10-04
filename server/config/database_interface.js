var config = require("./config.js");
var pg = require('pg');

module.exports = function() {
  return {
    query : function(inputQuery, callback){
			pg.connect(config.connection, function(err, client, done){
				var results = [];
				client.query("SET SEARCH_PATH = " + config.schema);
				var query = client.query(inputQuery);

				// Stream results back one row at a time
        query.on('row', function(row) {
            results.push(row);
        });

        query.on('end', function() {
            client.end();
            callback(results);
        });

        // Handle Errors
        if(err) {
          console.log(err);
        }
			});
		}
  };
};
