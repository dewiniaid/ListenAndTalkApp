var app = angular.module('app', ['ui.router', 'mgcrea.ngStrap', 'ngAnimate']);

app.config(function($stateProvider, $urlRouterProvider){
  $stateProvider
  .state('home',{
    url: '/',
    templateUrl: 'partials/home.html'
  })
  .state('about', {
    url: '/about',
    templateUrl: 'partials/about.html'
  });

  $urlRouterProvider.otherwise('/');

});
