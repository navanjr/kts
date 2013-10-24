import kpsFunctions

apiSettings = {
    'host': '192.168.49.149',
    'key': 'yadaydayda',
    'siteId': 27,
    'origin': 'kpsMike',
}

years = [2001]

menu = kpsFunctions.kps(
    apiSettings=apiSettings,
    yearsToProcess=years,
    pathToDBFs='c:\\client\\dosdata\\grant\\tax'
)

menu.menu()
