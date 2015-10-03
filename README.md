# Listen and Talk Web App
Web Application for Listen And Talk

# Development Tips
## Install Tools

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
```

## Update dependencies before you run
Run the following command
```
npm install && bower install && grunt default
```

## To Run
Run the following command
```
nodemon server.js
```

## If you have added new dependency
Run the following command
```
grunt default
```

## Clean Before Commit
Run the following command
```
grunt clean
```
