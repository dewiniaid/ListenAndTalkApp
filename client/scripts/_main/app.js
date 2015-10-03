var app = angular.module('app', ['ui.router', 'mgcrea.ngStrap', 'ngAnimate', 'restangular', 'auth0', 'angular-storage', 'angular-jwt']);

app.config(function($stateProvider, $urlRouterProvider, authProvider, $httpProvider, jwtInterceptorProvider){
  authProvider.init({
    domain: 'listentalk.auth0.com',
    clientID: 'pCGXGZvE7a7aNkEXi0YHS9WEp4Tw9N6Y',
    loginState: 'login'
  });

  jwtInterceptorProvider.tokenGetter = ['store', function(store) {
    // Return the saved token
    return store.get('token');
  }];

  $httpProvider.interceptors.push('jwtInterceptor');

  $stateProvider
  .state('home',{
    url: '/',
    controller: 'homeCtrl',
    templateUrl: 'partials/home.html',
    data: { requiresLogin: true }
  })
  .state('test', {
    url: '/test',
    controller: 'homeCtrl',
    templateUrl: 'partials/test.html'
  })
  .state('about', {
    url: '/about',
    templateUrl: 'partials/about.html'
  })
  .state('login', { 
    url: '/login', 
    templateUrl: 'partials/login.html', 
    controller: 'loginCtrl' 
  })
  // .state('userInfo', { 
  //   url: '/userInfo', 
  //   templateUrl: 'partials/userInfo.html', 
  //   controller: 'userInfoCtrl',
  //   requiresLogin: true 
  // })

  $urlRouterProvider.otherwise('/');

})
.run(function(auth) {
  // This hooks al auth events to check everything as soon as the app starts
  auth.hookEvents();
});



app
.run(function($rootScope, auth, store, jwtHelper, $location) {
  // This events gets triggered on refresh or URL change
  $rootScope.$on('$locationChangeStart', function() {
    var token = store.get('token');
    if (token) {
      if (!jwtHelper.isTokenExpired(token)) {
        if (!auth.isAuthenticated) {
          auth.authenticate(store.get('profile'), token);
        }
      } else {
        // Either show the login page or use the refresh token to get a new idToken
        $location.path('/');
      }
    }
  });
});
