var test = require("../server/controllers/cTest.js");

module.exports = function(app) {
  app.get('/api/test', function(req, res) {
    test.test(req, res);
  });
};
