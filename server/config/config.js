module.exports = function(){
  return {
    server_port : 8081,
    models_path :  __dirname + "/../server/models",
    hostname : 'latpostgresql.chk1nvtjtlku.us-west-2.rds.amazonaws.com',
    port : 5432,
    database_name : 'postgres',
    schema : 'listenandtalk,public',
    username : 'backend',
    password : 'Fq7DzXcOhw1ccqrHCwSQ',
    connection : "postgres://backend:Fq7DzXcOhw1ccqrHCwSQ@latpostgresql.chk1nvtjtlku.us-west-2.rds.amazonaws.com:5432/postgres"
  };
}();
