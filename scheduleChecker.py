# ConsuladoChecaAgendamento
# Acessa website do consulado brasileiro em Lisboa
# e checa se ha data disponivel para agendamento para
# determinadas modalidades pre-configuradas

#import smtplib
import configparser
import time
import logging
import playsound
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScheduleChecker:

    # Message/Alert types
    ALERT_LOGIN = 0
    ALERT_CAPTCHA = 1
    ALERT_SCHEDULE_FOUND = 2

    def __init__(self, configpath='./scheduleChecker.conf'):
        
        logging.basicConfig(filename='scheduleChecker.log', encoding='utf-8', level=logging.ERROR, format='%(asctime)s %(levelname)s:%(message)s')
        self.logger = logging.getLogger('ScheduleChecker')
        self.logger.setLevel(logging.INFO)
        
        self.configpath = configpath
        self.readConf()
        self.initDriver()
    
    def initDriver(self):
        try:
            options = webdriver.ChromeOptions()
            #options.add_argument('--user-data-dir=' + self.userDataPath)
            options.add_argument("--start-maximized")
            self.driver = webdriver.Chrome(executable_path=self.webdriverPath, options=options)
            self.driver.implicitly_wait(self.driverImplicityWait)
        except:
            self.logger.exception('Error loading webdriver on %s', self.webdriverPath)
            exit(2)

    def readConf(self):
        try:
            config = configparser.RawConfigParser()
            config.read(self.configpath, encoding="utf-8")
            
            self.userDataPath = config['general']['user.data.path']
            self.webdriverPath = config['general']['webdriver.path']
            self.maxChecks = int(config['general']['maxChecks'])
            self.messageType = config['general']['message.type']
            self.playScheduleFoundAlertPath = config['general']['alert.audio.scheduleFound.path']
            self.playCaptchaAlertPath = config['general']['alert.audio.captcha.path']
            self.playLoginAlertPath = config['general']['alert.audio.login.path']
            
            self.cpf = config['auth']['gov.br.cpf']
            self.password = config['auth']['gov.br.password']
            self.wppTarget = config['auth']['wpp.target']
            self.emailTarget = config['auth']['email.target']
            self.emailSender = config['auth']['email.sender']
            self.emailPass = config['auth']['email.sender.pass']
            self.smtpServerHost = config['auth']['smtp.server.host']
            self.smtpServerPort = int(config['auth']['smtp.server.port'])
            
            self.initUrl = config['url']['page.initial']
            self.loginUrl = config['url']['page.login']
            self.scheduleUrl = config['url']['page.schedule']
            self.wppUrl = config['url']['page.wpp.web']
            
            self.driverImplicityWait = int(config['time']['webdriver.implicitywait'])
            self.refreshTime = int(config['time']['refreshSchedulePage'])
            self.checkTime = int(config['time']['checkTime'])
            self.wppTimeBeforeClose = int(config['time']['timeToCloseWpp'])
            
            self.subjects = config['subject']
        except:
            self.logger.exception('Error reading properties from file %s', self.configpath)
            exit(1)
            
    def checkAvailability(self):
        self.logger.info('Checking schedule availability every {} seconds...'.format(self.refreshTime))
        self.logger.info('Opening page: {}'.format(self.scheduleUrl))
        self.driver.get(self.scheduleUrl)
        
        while True:
            self.searchForDates()
            self.logger.info('Waiting {} seconds before a new verification'.format(self.refreshTime))
            time.sleep(self.refreshTime)
        
    def login(self):
        
        self.logger.info('Loging in on GOV.BR')
        
        loginBtn = self.driver.find_element_by_id('loginunico-btn')
        loginBtn.click()
        
        cpfField = self.driver.find_element_by_id('accountId')
        cpfField.send_keys(self.cpf)
        
        btnSend = self.driver.find_element_by_class_name('button-continuar')
        btnSend.click()
        
        passField = self.driver.find_element_by_id('password')
        passField.send_keys(self.password)
        
        submitBtn = self.driver.find_element_by_id('submit-button')
        submitBtn.click()
        
        # Wait until captcha is solved by the user
        count = 1
        while self.hasCaptcha() and count <= self.maxChecks:
            self.logger.debug('Sending message about captcha...')
            self.sendMessage(self.ALERT_CAPTCHA, '[Try ' + str(count) + '] Solve captcha needed! Waiting ' + str(self.checkCaptchaSolvedTime) + ' seconds...')
            time.sleep(self.checkTime)
            count += 1
        
        self.logger.info('Login done')
        
    def hasCaptcha(self):
        self.logger.debug('Checking if there is a captcha on the page... page title is: ' + self.driver.title)
        
        #TODO Check if there is a captcha to solve
        challenge = 'gov' in self.driver.title

        self.logger.info('Needs captcha? ' + str(challenge))
        return challenge
  
    def searchForDates(self):
    
        self.logger.info('Checking if there is a spot available for the selected subjects on configuration file')
        foundSomething = False
        
        checks = 1
        while self.needsLogin() and checks <= self.maxChecks:
            self.sendMessage(self.ALERT_LOGIN)
            checks += 1
            time.sleep(self.checkTime)
            
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

    def needsLogin(self):
        time.sleep(1)
        self.logger.debug('Checking if it needs a login... page url: {}, page title: {}'.format(self.driver.current_url, self.driver.title))
        isLoginPage = self.driver.current_url == self.loginUrl or 'gov' in self.driver.title
        self.logger.info('Needs login? ' + str(isLoginPage))
        return isLoginPage
        
    def sendMessage(self, alertType, message=None):
        
        if message:
            self.logger.info(message)
            print(message)
        
        # if self.messageType and self.messageType != 'None':
            # if self.messageType in ['WPPWEB', 'ALL']:
                # self.sendByWpp(message)
            # if self.messageType == ['EMAIL', 'ALL']:
                # self.sendByEmail(message)
            # if self.messageType in ['BEEP', 'ALL']:
                # self.beep(alertType)
            # if self.messageType in ['PLAY', 'ALL']:
        self.playMessage(alertType)
        
        self.logger.info('Message sent')
        
    # def sendByWpp(self, message):
    
        # self.logger.info('Sending message by WhatsApp Web...')
        
        # self.logger.debug('Open WhatsApp Web in a new tab')
        # self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 't')
        # self.driver.get(self.wppUrl.format(self.wppTarget, message))
               
        # sendButton = self.driver.find_element_by_class_name('_4sWnG')
        # sendButton.click()
        
        # self.logger.debug('Wait for the configured amount of seconds and close tab')
        # time.sleep(self.wppTimeBeforeClose)
        # self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 'w')
        
        # self.logger.info('Message sent by WhatsApp Web!')
        
    # def sendByEmail(self, message):
        
        # self.logger.info('Sending message by Email...')
        # try:        
            # email_text = """\
            # From: %s
            # To: %s
            # Subject: %s

            # %s
            # """ % (self.emailSender, self.emailTarget, 'New spot available!', message)
            
            # self.server = smtplib.SMTP_SSL(self.smtpServerHost, self.smtpServerPort)
            # self.server.ehlo()
            # server.login(self.emailSender, self.emailPass)
            # server.sendmail(self.emailSender, self.emailTarget, email_text)
            # server.close()
            # self.logger.info('Message sent by Email!')
        # except:
            # self.logger.exception('Error sending email using ' + str(self.emailServer))
            
    # def beep(self, isCaptcha=False):
        # self.logger.debug('Beeping...')
        
        # for i in range(0, 10):
            # winsound.MessageBeep(winsound.MB_ICONASTERISK)
            # time.sleep(1)
        
        # self.logger.debug('Beeping done')
        
    def playMessage(self, alertType):
    
        self.logger.debug('Received alert: {}'.format(alertType))
        
        if alertType == self.ALERT_LOGIN:
            audioPath = self.playLoginAlertPath
        elif alertType == self.ALERT_CAPTCHA:
            audioPath = self.playCaptchaAlertPath
        elif alertType == self.ALERT_SCHEDULE_FOUND:
            audioPath = self.playScheduleFoundAlertPath

        self.logger.debug('Playing: {}'.format(audioPath))
        playsound.playsound(audioPath)

def main():
    app = ScheduleChecker()
    app.checkAvailability()

if __name__ == "__main__":
    main()