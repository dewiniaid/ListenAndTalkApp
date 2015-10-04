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
    views: {
      "nav_top": {
        controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
        controller: 'homeCtrl',
        templateUrl: "partials/home.html"
      }
    },
    data: { requiresLogin: true }
  })
  .state('newstudent', {
    url: '/newstudent',
    views: {
      "nav_top": {
        controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
        controller: 'studentsCtrl',
        templateUrl: "partials/newstudent.html"
      }
    }
  })
  .state('markAttendance', {
    url: '/markAttendance',
    views: {
      "nav_top": {
        controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
        controller: 'studentsCtrl',
        templateUrl: "partials/markAttendance.html"
      }
    },
    data: { requiresLogin: true }
  })
  .state('viewAttendance', {
    url: '/viewAttendance',
    views: {
      "nav_top": {
          controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
        controller: 'studentsCtrl',
        templateUrl: "partials/viewAttendance.html"
      }
    },
    data: { requiresLogin: true }
  })
  .state('settings', {
    url: '/settings',
    views: {
      "nav_top": {
        controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
				controller: 'settingCtrl',
        templateUrl: "partials/settings.html"
      }
    },
    data: { requiresLogin: true }
  })
  .state('login', {
    url: '/login',
    views: {
      "main": {
        controller: 'loginCtrl',
        templateUrl: "partials/login.html"
      }
    }
  })
  .state('userinfo', {
    url: '/userinfo',
    views: {
      "nav_top": {
        controller: 'homeCtrl',
        templateUrl: "partials/navTop.html"
      },
      "main": {
        controller: 'homeCtrl',
        templateUrl: "partials/userinfo.html"
      }
    },
    data: { requiresLogin: true }
  })

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
