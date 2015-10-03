module.exports = (function(){
    return {
      test : function(req, res){
        res.status(200).send("OK :D");
      },
      test_params: function(req, res){
        res.status(200).json(
          {
            msg: "Recieved params[id]: " + req.params.id
          }
        );
      }
    }
})();
