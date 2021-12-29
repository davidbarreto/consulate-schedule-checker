class AlertPrinter:
    def alert(alertType, message=None):
        print('ALERT [{}]: {}'.format(alertType, message))