module.exports = function(grunt) {
  grunt.initConfig({
    clean: [
      "node_modules",
      "client/vendor"
    ],
    wiredep: {
      task: {
        src: [
          'client/index.html'
        ]
      }
    },
    injector: {
      options: {
        ignorePath: 'client/'
      },
      local_dependencies: {
        files: {
          'client/index.html': ['client/scripts/**/*.js', 'client/stylesheets/*.css'],
        }
      }
    }
  });
  grunt.loadNpmTasks('grunt-contrib-clean');
  grunt.loadNpmTasks('grunt-wiredep');
  grunt.loadNpmTasks('grunt-injector');

  grunt.registerTask('default', ['wiredep', 'injector']);

}
