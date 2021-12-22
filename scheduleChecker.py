# ConsuladoChecaAgendamento
# Acessa website do consulado brasileiro em Lisboa
# e checa se ha data disponivel para agendamento para
# determinadas modalidades pre-configuradas

import smtplib
import configparser
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScheduleChecker:

    def __init__(self, configpath='./scheduleChecker.conf'):
        self.configpath = configpath
        self.readConf()
    
    def initDriver(self):
        try:
            options = webdriver.ChromeOptions()
            #options.add_argument('--user-data-dir=' + self.userDataPath)
            self.driver = webdriver.Chrome(executable_path=self.webdriverPath, options=options)
            self.driver.implicitly_wait(self.driverImplicityWait)
        except:
            logging.exception('Error loading webdriver on %s', self.webdriverPath)
            exit(2)

    def readConf(self):
        try:
            config = configparser.RawConfigParser()
            config.read(self.configpath)
            
            self.userDataPath = config['general']['user.data.path']
            self.webdriverPath = config['general']['webdriver.path']
            self.messageType = config['general']['message.type']
            
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
            self.checkCaptchaSolvedTime = int(config['time']['checkCaptchaSolved'])
            self.wppTimeBeforeClose = int(config['time']['timeToCloseWpp'])
            
            self.maxCaptchaChecks = int(config['retry']['maxCaptchaChecks'])
            self.subjects = config['subject']
        except:
            logging.exception('Error reading properties from file %s', self.configpath)
            exit(1)
            
    def checkAvailability(self):
        logging.info('Opening schedule page')
        logging.debug('page: ' + self.scheduleUrl)
        self.driver.get(self.scheduleUrl)
        
        while True:
            self.searchForDates()
            time.sleep(self.refreshTime)
        
    def login(self):
        
        logging.info('Loging in on GOV.BR')
        
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
        while self.hasCaptcha() and count >= self.maxCaptchaChecks:
            self.sendMessage('[Try ' + count + '] Solve captcha needed! Waiting ' + str(self.checkCaptchaSolvedTime) + ' seconds...')
            time.sleep(self.checkCaptchaSolvedTime)
            count += 1
        
        logging.info('Login done')
        
    def hasCaptcha(self):
        logging.debug('Checking if there is a captcha on the page...')
        
        #TODO Check if there is a captcha to solved
        challenge = 'gov' in self.driver.current_url

        logging.info('Needs captcha? ' + str(challenge))
        return challenge
  
    def searchForDates(self):
    
        logging.info('Checking if there is a spot available')
        foundSomething = False
        if self.needsLogin():
            self.login()
            
        logging.debug('Selected subjects: ' + self.subjects)
        
        table = self.driver.find_element_by_class_name('table table-striped')
        rows = table.find_element_by_tag_name('tr') # get all of the rows in the table
        for row in rows:
            # Get the columns (all the column 2)    
            elem = row.find_element_by_tag_name('td')
            for key, subject in self.subjects:
                if elem[0] == subject and 'Indisponível' not in elem[1]:
                    self.sendMessage('ATENTION: There is a spot for ' + str(elem[0]) + ' on ' + str(elem[1]))
                    foundSomething = True
            
        if not foundSomething:
            logging.info('Not found an available spot for the selected subjects')
                   
    def needsLogin(self):
        logging.debug('Checking if it needs a login... Page URL: ' + self.driver.current_url)
        isLoginPage = 'login' in self.driver.current_url
        logging.info('Needs login? ' + str(isLoginPage))
        return isLoginPage
        
    def sendMessage(self, message):
        logging.info('Sending message: ' + message)
        
        if self.messageType in ['WPPWEB', 'ALL']:
            sendByWpp(message)
        if self.messageType == ['EMAIL', 'ALL']:
            sendByEmail(message)
        if self.messageType in ['BIP', 'ALL']:
            bip()
        
        logging.info('Message sent')
        
    def sendByWpp(self, message):
    
        logging.info('Sending message by WhatsApp Web...')
        
        logging.debug('Open WhatsApp Web in a new tab')
        self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 't')
        self.driver.get(self.wppUrl.format(self.wppTarget, message))
               
        sendButton = self.driver.find_element_by_class_name('_4sWnG')
        sendButton.click()
        
        logging.debug('Wait for the configured amount of seconds and close tab')
        time.sleep(self.wppTimeBeforeClose)
        self.driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 'w')
        
        logging.info('Message sent by WhatsApp Web!')
        
    def sendByEmail(self, message):
        
        logging.info('Sending message by Email...')
        try:        
            email_text = """\
            From: %s
            To: %s
            Subject: %s

            %s
            """ % (self.emailSender, self.emailTarget, 'New spot available!', message)
            
            self.server = smtplib.SMTP_SSL(self.smtpServerHost, self.smtpServerPort)
            self.server.ehlo()
            server.login(self.emailSender, self.emailPass)
            server.sendmail(self.emailSender, self.emailTarget, email_text)
            server.close()
            logging.info('Message sent by Email!')
        except:
            logging.exception('Error sending email using ' + str(self.emailServer))
            
    def bip(self, message):
        logging.info('Biping...')
        
        
        
        logging.info('Bipping done')

def main():
    logging.basicConfig(filename='scheduleChecker.log', encoding='utf-8', level=logging.DEBUG)
    app = ScheduleChecker()
    #app.checkAvailability()
    app.bip('teste')

if __name__ == "__main__":
    main()