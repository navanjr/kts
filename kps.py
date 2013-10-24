import kpsFunctions

apiSettings = {
    'host': '192.168.49.149',
    'key': 'yadaydayda',
    'siteId': 69,
    'origin': 'kpsMike',
}

years = [2006]

menu = kpsFunctions.kps(
    apiSettings=apiSettings,
    yearsToProcess=years,
    pathToDBFs='c:\\client\\dosdata\\stephens\\tax'
)

menu.menu()
