from importlib import import_module
import configparser
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScheduleChecker:

    '''
    A class that checks brazilian consulate website looking for 
    an available schedule to selected subjects. Selenium is required for that.
    The login is made manually where the system will alert you to log in into the website
    The system will also alert you if it finds an schedule available to one or more subjects.
    
    The class setup is made by a configuration file on INI format.
    
    On the config file, you must to provide the subjects that will be checked,
    as well as the list of alert senders.
    
    * SUBJECTS:
    The subjects must be placed on "subject" section on config file, this way:
    
    [subject]
    subject.1 = CNH - Declaração
    subject.2 = Certificado de Nacionalidade para Estatuto de Igualdade
    ...
    
    * ALERT SENDERS:
    A coulple of alert senders is provided as an example, but you can provide your own.
    
    The alert senders must implement the method:
    def alert(alertType, message=None)
        # do something
    '''

    # Message/Alert types
    ALERT_LOGIN = 1
    ALERT_SCHEDULE_FOUND = 2

    def __init__(self, configpath='./scheduleChecker.conf'):
        
        self.logger = logging.getLogger('ScheduleChecker')
        self.configpath = configpath
        self.alertSenders = []
        
        self.readConf()
        self.initDriver()
        self.addAlertSenders()
    
    def initDriver(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(executable_path=self.webdriverPath, options=options)
            self.driver.implicitly_wait(self.driverImplicityWait)
        except:
            self.logger.exception('Error loading webdriver on %s', self.webdriverPath)
            exit(2)

    def readConf(self):
        try:
            self.logger.info('Reading configuration file: {}'.format(self.configpath))
            config = configparser.RawConfigParser()
            config.read(self.configpath, encoding="utf-8")
            
            self.maxLoginChecks = int(config['retry']['maxLoginChecks'])
            
            self.loginUrl = config['uri']['url.login']
            self.scheduleUrl = config['uri']['url.schedule']
            self.webdriverPath = config['uri']['path.webdriver'] 
            
            self.driverImplicityWait = int(config['time']['webdriver.implicitywait'])
            self.refreshTime = int(config['time']['refreshSchedulePage'])
            self.waitForLogin = int(config['time']['waitForLogin'])
            
            self.subjects = config['subject']
            self.alerts = config['alert']
            
        except:
            self.logger.exception('Error reading properties from file %s', self.configpath)
            exit(1)
            
    def addAlertSenders(self):
        
        self.logger.info('Adding alert classes as configured on configuration file')
        for key in self.alerts:
            alertName = self.alerts[key]
            self.logger.debug('Instantiating class {}'.format(alertName))
            self.alertSenders.append(self.getClass(alertName))
            
    def getClass(self, classStr):
        try:
            module_path, class_name = classStr.rsplit('.', 1)
            module = import_module('{}.{}'.format(module_path, class_name))
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            self.logger.exception('Error importing alert class %s', classStr)
            raise ImportError(classStr)
            
    def checkAvailability(self):
        self.logger.info('Checking schedule availability every {} seconds...'.format(self.refreshTime))
        self.logger.info('Opening page: {}'.format(self.scheduleUrl))
        self.driver.get(self.scheduleUrl)
        
        while True:
            self.searchForDates()
            self.logger.info('Waiting {} seconds before a new verification'.format(self.refreshTime))
            time.sleep(self.refreshTime)
    
    def searchForDates(self):
    
        self.logger.info('Checking if there is a spot available for the selected subjects on configuration file')
        foundSomething = False
        
        self.checkLogin()
            
        self.logger.info('Refreshing page: {}'.format(self.scheduleUrl))
        self.driver.get(self.scheduleUrl)
        
        # Get the table on the page. Discard the table header
        rows = self.driver.find_elements_by_tag_name('tr')[1:]
        self.logger.debug('Got {} rows'.format(len(rows)))
        
        foundSomething = False
        
        # For each subject configured on the configuration file,
        # find it on the table and verify if it has an available schedule
        for key in self.subjects:
            
            selectedSubject = self.subjects[key]
            self.logger.info('Verifying if there is a spot available to {}'.format(selectedSubject))
            
            for row in rows:
                
                self.logger.debug('Processing row...')
                columns = row.find_elements_by_xpath(".//td[@class='align-middle']")
                self.logger.debug('Got {} columns'.format(len(columns)))
                subject = columns[0].text
                schedule = columns[1].text
            
                if selectedSubject == subject and 'Indisponível' not in schedule:
                    self.sendMessage(self.ALERT_SCHEDULE_FOUND , 'ATENTION: There is a spot for {} on {}'.format(subject, schedule))
                    foundSomething = True

        if not foundSomething:
            self.logger.info('Not found any available spot for the selected subjects')
            
    def checkLogin(self):
        checks = 1
        while self.needsLogin() and checks <= self.maxLoginChecks:
            self.logger.debug('Try {}/{}: Logging needed!'.format(checks, self.maxLoginChecks))
            self.sendMessage(self.ALERT_LOGIN, 'Please, login into the system!')
            checks += 1
            time.sleep(self.waitForLogin)
            
        if checks > self.maxLoginChecks:
            raise Exception('Exeeded maximum login tries')

    def needsLogin(self):
        self.logger.debug('Checking if it needs a login... page url: {}, page title: {}'.format(self.driver.current_url, self.driver.title))
        isLoginPage = self.driver.current_url == self.loginUrl or 'gov' in self.driver.title
        self.logger.info('Needs login? ' + str(isLoginPage))
        return isLoginPage
        
    def sendMessage(self, alertType, message=None):
     
        self.logger.debug('Alert = {}, Message = {}'.format(alertType, message))
        self.logger.debug('Calling [{}] alert senders as configured on configuration file'.format(len(self.alertSenders)))
        for sender in self.alertSenders:
            sender.alert(alertType, message)

