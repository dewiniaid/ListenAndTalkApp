module.exports = (function(){
    return {
      getAllStudents : function(req, res){
        res.status(200).send("All the students are returned");
      },
      getStudentById : function(req, res){
        res.status(200).send("Student returned by ID");
      },
      putStudentById : function(req, res){
        res.status(200).send("Student are put on this endpoint");
      },
      addNewStudent : function(req, res){
        res.status(200).send("Student are added on this endpoint");
      },
      getStudentsActivities : function(req, res){
        res.status(200).send("Find students by activities");
      }
    }
})();
