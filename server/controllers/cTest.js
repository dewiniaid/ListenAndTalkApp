module.exports = (function(){
    return {
      test : function(req, res){
        res.status(200).send("OK :D");
      }
    }
})();
