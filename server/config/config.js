module.exports = function(){
  return {
    server_port : 4000,
    models_path :  __dirname + "/../server/models",
    hostname : 'listenandtalk.cloudapp.net',
    port : 5432,
    database_name : 'postgres',
    schema : 'listenandtalk,public',
    username : 'backend',
    password : 'BNC8HYC2xIKmHsEDBmNx',
    connection : "postgres://backend:BNC8HYC2xIKmHsEDBmNx@listenandtalk.cloudapp.net:5432/postgres"
  };
}();
