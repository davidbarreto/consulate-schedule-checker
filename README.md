# ConsulateScheduleChecker

> This software aims to help all people that are trying a spot on the Brazilian consulate by the e-consular system and is not finding anyone.
> I personally spent more than 2 months and didn't manage to find any spot on the consulate schedule, mainly for the 'CNH' subject.
> I hope that using this simple script you can schedule your appointment as soon as possible!

The script frequently checks if there is a spot available for an in-person appointment at the Brazilian consulate website (e-consular).
The login on e-consular is manual and the script will alert you when it is needed. Just login into the e-consular, and let the script check the available spots.

You have to setup on the configuration file all the subjects that you want to monitor (exactly as it appears on the e-consular)
If the script finds a spot available for one or more subjects, you will be notified.

## Configuration file

By default, the script reads a configuration file named 'scheduleChecker.conf' on the root directory.
This file is in INI format and contains the settings required by the script.

* maxLoginChecks -> How many times the system will check if a login is needed. If no login is provided after this quantity of checks, the script will raise an error
* webdriver.implicitywait -> The max number of seconds the Chrome webdriver from selenium will wait for the elements that it is finding on the HTML
* refreshSchedulePage -> The quantity of seconds the script will wait until the next chek for a spot available
* waitForLogin -> How many seconds the script will wait before check if a login is needed again
* url.schedule -> The URL for the consulate schedule page
* url.login -> The URL for the consulate login page
* path.webdriver -> Path to the Crhome driver on your machine (see the section 'Dependencies')

It's important to keep the enconding of this file as UTF-8

### Subjects

You have to define all subjects you want to monitor on the 'subject' section on the configuration file. The subjects have to be written the same as on the consulate website. For the Brazilian consulate in Lisbon, you can check it [here](https://ec-lisboa.itamaraty.gov.br/availability) (login needed).

One or more subjects must be defined inside the section. There is no limit to the number of subjects defined. You can use the following syntax:

```
[subject]

subject.1 = CNH - Declaração
subject.2 = Passaporte para criança (menor de 18 anos) - com presença de AMBOS os pais brasileiros
```

### Alerts

This solution uses external modules to provide the alert feature. These modules are configured on the configuration file, section 'alert'.
So when a login is needed or when a spot was found on the schedule, these modules are called, one by one.
There is a module provided here that alerts the user through a voice (mp3 recording) saying the alert messages.

The alerts have to be configured as follows:

```
[alert]

alert.1 = package.MyClass
```

PS: It's already provided the alert module 'alerts.player.SoundAlertPlayer'

> If you want to write your alert code (let's say, to send an e-mail, SMS, or WhatsApp message when an alert has to be sent), you have to implement the method:
```
def alert(alertType, message=None)
	# do something
```
> 'alertType' is the type of alert generated, and 'message' is the message of this alert.
> The 'alertType' parameter can be ScheduleChecker.ALERT_LOGIN or ScheduleChecker.ALERT_SCHEDULE_FOUND (with values 1 and 2 respectively, but it's better to import the ScheduleChecker class and use those constants)
> The message parameter can be omitted.
> You can follow the examples on this source code (alerts.player.SoundAlertPlayer and alerts.printer.AlertPrinter)

## Run

In order to run the script, Python must be installed on your system. After place the source code on your machine, just execute the main script as follow:

```
python checker.py
```

## Login

It's important to notice that sometimes the captcha returns that the answer is wrong (when apparently it's not).
This scenario occurs probably due to the use of test automation software as Selenium.
So it's recommended to use another login method such as the login by QR code, through the gov.br mobile app.

## Log

By default, the script writes log records on file 'scheduleChecker.log'.

## Dependencies:

The system was tested using Python 3.9.9

All module dependencies can be installed by the command
```
pip install <module>
```

### core:
- selenium 4.1.0
- [Chrome WebDriver](https://chromedriver.chromium.org/downloads)

### player alert:
- playsound 1.2.2

If you found a bug or have suggestions, please contact me