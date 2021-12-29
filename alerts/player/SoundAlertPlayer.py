import os
import playsound
from core.ScheduleChecker import ScheduleChecker

class SoundAlertPlayer:
    def alert(alertType, message=None):
        
        path = os.path.dirname(os.path.realpath(__file__))
        
        if alertType == ScheduleChecker.ALERT_LOGIN:
            audioPath = path + '/login_alert_en.mp3'
        elif alertType == ScheduleChecker.ALERT_SCHEDULE_FOUND:
            audioPath = path + '/schedule_alert_en.mp3'
            
        print('Playing {}'.format(audioPath))
        playsound.playsound(audioPath)