var config = require("./config/config.js");
var path = require("path");

var express = require("express");
var jwt = require('express-jwt');

var jwtCheck = jwt({
  secret: new Buffer('B0ap21JvYBt506Hm6BuRMwL0suhGSVatesLy8AJM1Htpixir9-I-bO4EIoiaZkwy', 'base64'),
  audience: 'pCGXGZvE7a7aNkEXi0YHS9WEp4Tw9N6Y'
});

var server = express();
server.use(express.static(path.join(__dirname, "./client")));

var bodyParser = require("body-parser");
server.use(bodyParser.json());
server.use(bodyParser.urlencoded({ extended: true }));

require("./config/routes.js")(server);

server.listen(config.server_port, function(){
  console.log("Listening on port " + config.server_port);
})
