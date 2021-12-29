import logging
from core.ScheduleChecker import ScheduleChecker

def main():

    logging.basicConfig(filename='scheduleChecker.log', encoding='utf-8', level=logging.ERROR, format='%(asctime)s %(levelname)s:%(message)s')
    logging.getLogger('ScheduleChecker').setLevel(logging.INFO)
    
    app = ScheduleChecker()
    app.checkAvailability()

if __name__ == "__main__":
    main()