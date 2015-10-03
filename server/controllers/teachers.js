module.exports = (function(){
    return {
      getTeacherInfo : function(req, res){
        res.status(200).send("Teacher returned by ID");
      },
      updateTeacherInfo : function(req, res){
        res.status(200).send("Teacher are updated on this endpoint");
      },
      addNewTeacher : function(req, res){
        res.status(200).send("Teacher are added on this endpoint");
      }
    }
})();
