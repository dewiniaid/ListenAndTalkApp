# Listen and Talk Web App
Web Application for Listen And Talk

# Development
## 1. Install Tools

For Mac OS
```
brew install node
sudo npm install -g grunt-cli
sudo npm install -g bower
sudo npm install -g nodemon
```

For Windows
```
npm install -g grunt-cli
npm install -g bower
npm install -g nodemon
```

## 2. Update dependencies before you run
Run the following command
```
npm install && bower install && grunt default
```

## 3. To Run
Run the following command
```
nodemon server.js
```

## [Optional] If you have added new dependency
Run the following command
```
grunt default
```

## [Optional] Clean Before Commit
Run the following command
```
grunt clean
```
