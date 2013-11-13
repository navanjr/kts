__author__ = 'nate'
import socket
import threading
import win32event
import select
import types

def log(message):
    try:
        file = open("c:\\client\\key\\notice.log", "a")
        file.write("%s\n" % message)
        file.close()
    except IOError:
        pass

class kirc:
    def __init__(self, network='irc.freenode.net', port=6667, menu=None):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((network, port))
        self.irc.setblocking(0)
        self.menu = menu

    def connect(self, nickname='natebot1', room='key_team'):
        self.nickname = nickname
        self.room = str(room).replace('#', '')
        self.send('NICK %s' % self.nickname)
        self.send('USER %s %s %s :Python IRC' % (self.nickname, self.nickname, self.nickname))
        self.send('JOIN #%s' % self.room)
        self.brain = personalResponses(self.nickname, self.room, self.menu)

    def send(self, message):
        self.irc.send('%s\r\n' % message)

    def psend(self, message):
        self.irc.send('PRIVMSG #%s :%s\r\n' % (self.room, message))

    def find(self, x):
        if self.data.find(x) != -1:
            return True
        else:
            return False

    def listenBackgroundThread(self):
        t = threading.Thread(name='api', target=self.listen)
        t.setDaemon(True)
        t.start()

    def ircMessageDecoder(self, sample):
        obj = {
            'sample': sample,
        }
        if len(sample.split()) > 4:
            obj['from'] = sample.split()[0]
            obj['type'] = sample.split()[1]
            obj['room'] = sample.split()[2]
            obj['to'] = sample.split()[3].replace(':', '')
            obj['chatString'] = ' '.join(sample.split()[4:])
        else:
            obj['from'] = None
            obj['type'] = None
            obj['room'] = None
            obj['to'] = None
            obj['chatString'] = None
        return obj

    def listen(self, socketTimeout=3):
        cont = True
        restartService = True
        ready = select.select([self.irc], [], [], socketTimeout)
        if ready[0]:
            self.data = self.irc.recv(4096)

            # log("raw data: %s" % self.ircMessageDecoder(self.data))
            log("raw data: %s" % self.data)

            brainResponse = self.brain.stimulate(self.ircMessageDecoder(self.data))

            log("response from my brain: %s" % brainResponse)

            if brainResponse["psend"]:
                if isinstance(brainResponse["psend"], types.ListType):
                    for psend in brainResponse["psend"]:
                        self.psend(psend)
                else:
                    self.psend(brainResponse["psend"])
            if brainResponse["chatCommand"]:
                self.send(brainResponse["chatCommand"])
            cont = brainResponse["continueChat"]
            restartService = brainResponse["restartService"]

        return cont, restartService


class personalResponses:
    def __init__(self, myNickName, whereAmI, menu):
        self.myNickname = myNickName
        self.myRoom = whereAmI
        self.menu = menu
        self.consciousness = {}
        self.subConsciousness = {}
        self.add("quit", "alrighty then... cya.", False, "QUIT", restartService=True)
        self.add("shutdown", "ok ill leave and wont return... cya.", False, "QUIT", restartService=False)
        self.add("marco", "polo")
        self.add("hi", "I already said hi...")
        self.add("hello", "I already said hi... :)")
        self.add("cheese", "um... im not really hungry.")

        self.add("PING", chatCommand="PONG {split1}", forSubConscious=True)
        self.add("KICK", chatCommand="JOIN #%s" % self.myRoom, forSubConscious=True)

    def add(self, keyword, pSendResponse=None, continueChat=True, chatCommand=None, forSubConscious=False, restartService=True):
        item = {
            "psend": pSendResponse,
            "continueChat": continueChat,
            "restartService": restartService,
            "chatCommand": chatCommand,
        }
        if not forSubConscious:
            item["cortex"] = "conscious"
            self.consciousness[keyword] = item
        else:
            item["cortex"] = "subConscious"
            self.subConsciousness[keyword] = item

    def dialect(self, psend=None, continueChat=True, chatCommand=None, cortex=None, restartService=True):
        return {"psend": psend, "continueChat": continueChat, "chatCommand": chatCommand, "cortex": cortex, "restartService": restartService}

    def stimulate(self, chatObj):
        if chatObj['to'] == self.myNickname:
            output = self.stimulate_conscious(chatObj)
            if not output:
                output = self.dialect(
                    psend="i can hear you but i don't understand you. (%s)" % chatObj['chatString'],
                    cortex="conscious"
                )
        else:
            output = self.stimulate_subConscious(chatObj)
            if not output:
                output = self.dialect()

        return output

    def stimulate_conscious(self, chatObj):
            # consciousness responses intended for me
            keyword = [keyword for keyword in self.menu.chatKeywords() if keyword in chatObj['chatString']]

            log('I am stimulated... keyword: %s' % keyword)

            if len(keyword) > 0:
                return self.dialect(psend=self.menu.chatCommand(keyword[0], chatObj))

            for key, value in self.consciousness.items():
                if key in chatObj['chatString']:
                    return value
            return None

    def stimulate_subConscious(self, chatObj):
        # subConsciousness responses intended for anyone
        #   might consider adding PING to the ircDecoder someday
        for key, value in self.subConsciousness.items():
            if key in chatObj['sample']:
                value["chatCommand"] = value["chatCommand"].format(split1=chatObj['sample'].split()[1]) if "{split1}" in value["chatCommand"] else value["chatCommand"]
                return value
        return None

