module.exports = (function(){
    return {
      getTeacherByEmail : function(req, res) {
        var query = {
            text: "SELECT * FROM staff WHERE email = $1",
            values: [req.params.email]
        };
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      getTeacherById : function(req, res){
        var query = {
            text: "SELECT * FROM staff WHERE id = $1",
            values: [req.params.id]
        };
        db.query(query, function(result){
          res.status(200).json(result);
        });
      },
      updateTeacherInfo : function(req, res){
        res.status(200).send("Teacher are updated on this endpoint");
      },
      addNewTeacher : function(req, res){
        res.status(200).send("Teacher are added on this endpoint");
      }
    }
})();
