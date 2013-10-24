import subprocess
import urllib2
import urllib
import base64
import json


def areYouSure(question='are you sure?', force=False, boolean=True):
    try:
        entered = raw_input("     %s ===> " % question)
    except KeyboardInterrupt:
        pass
    if boolean:
        if entered in ('yes', 'y'):
            return True
        else:
            return False
    else:
        return entered


def say(*what, **kwargs):
    if 'verbose' in kwargs:
        if kwargs['verbose'] == False:
            return
    for line in what:
        print '      %s' % line


def isnull(what,convertTo=''):
    if what is None:
        return convertTo
    return str(what)


def getTextFromFile(commandArray):
    raw = subprocess.Popen(commandArray, stdout=subprocess.PIPE, shell=True)
    (out, err) = raw.communicate()
    return out, err


def runDos(command):
    run = subprocess.Popen(r'%s' % command, shell=True)
    run.wait()


def apiCall(host, apiKey, resource="v2/treasurer/sites.json", data=None, debug=False):
    url = 'http://%s/%s' % (host, resource)
    if data:
        data = json.dumps(data, separators=(',', ':'))
        data = 'site_id=27&rows=%s' % urllib.quote(data)
    req = urllib2.Request(url, data)
    auth = 'Basic ' + base64.urlsafe_b64encode("%s:%s" % (apiKey, ''))
    req.add_header('Authorization', auth)

    # req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 5.1; rv:10.0.1) Gecko/20100101 Firefox/10.0.1')

    # handler = urllib2.HTTPHandler(debuglevel=1)
    # opener = urllib2.build_opener(handler)
    # urllib2.install_opener(opener)

    if not debug:
        try:
            # print "INFO method = ", req.get_method()
            # print "INFO data = ", req.get_data()

            response = urllib2.urlopen(req, data, 10)
            # print response.read()

            # print "INFO url = ", response.geturl()
            # print "INFO code = ", response.code
        except (urllib2.HTTPError, urllib2.URLError) as e:
            print 'Oops... error', e
            try:
                print e.read()
            except AttributeError:
                pass
            return False, e
        try:
            decodedResponse = json.load(response)
        except ValueError as e:
            # print 'JSON Decoding issue:', response.read()
            # print response.read()
            print 'headers', response.headers
            return False, e

        return True, decodedResponse

    else:
        print 'debug', req

