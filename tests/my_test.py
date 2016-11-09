#!/Applications/Shotgun.app/Contents/Frameworks/Python/bin/python

#!/usr/bin/python

# Import Toolkit so we can access to Toolkit specific features.
import sgtk
from PySide import QtGui, QtCore
app = QtGui.QApplication([])


def ouin():
    print "Ouin...\n\n"

# Import the ShotgunAuthenticator from the tank_vendor.shotgun_authentication
# module. This class allows you to authenticate either programmatically or, in this # noqa
# case, interactively.
from tank_vendor.shotgun_authentication import ShotgunAuthenticator
from tank.authentication import interactive_authentication

# Instantiate the CoreDefaultsManager. This allows the ShotgunAuthenticator to
# retrieve the site, proxy and optional script_user credentials from shotgun.yml # noqa
# cdm = sgtk.util.CoreDefaultsManager()

# Instantiate the authenticator object, passing in the defaults manager.
# authenticator = ShotgunAuthenticator(cdm)
authenticator = ShotgunAuthenticator()

# Optionally clear the current user if you've already logged in before.
authenticator.clear_default_user()

# Get an authenticated user. In this scenario, since we've passed in the
# CoreDefaultsManager, the code will first look to see if there is a script_user inside # noqa
# shotgun.yml. If there isn't, the user will be prompted for their username,
# password and optional 2-factor authentication code. If a QApplication is
# available, a UI will pop-up. If not, the credentials will be prompted
# on the command line. The user object returned encapsulates the login
# information.
print "BEFORE"
user = authenticator.get_user()
print "AFTER"
# user.set_session_token('873a57e8503855d50c9148e99572b322')
# print "User is '%s'" % user

# Tells Toolkit which user to use for connecting to Shotgun. Note that this should # noqa
# always take place before creating a Sgtk instance.
sgtk.set_authenticated_user(user)

# timer = QtCore.QTimer()
# timer.timeout.connect(ouin)
# timer.start(5000)

# loop = QtCore.QEventLoop()

# from shotgun_api3 import Shotgun
# print Shotgun('https://hubertp-sso.shotgunstudio.com', session_token='xxx').info()
from pprint import pprint
import time
sg = user.create_sg_connection()

# for i in range(1,11):
start_stamp = last_stamp = int(time.time())
# for i in range(1,31):
for i in range(1,501):
    new_stamp = int(time.time())
    delta = new_stamp - last_stamp
    last_stamp = new_stamp
    print "-----> %d - %s - %d" % (i, user.impl.get_session_expiration(), delta)
    # print "-----> %s" % i
    if time.time() > user.impl.get_session_expiration() + 15:
        interactive_authentication.renew_session(user.impl, no_gui=True)
    # pprint(sg.find('Project', [], ['id', 'name']))
    sg.find('Project', [], ['id', 'name'])
    # time.sleep(60)
    # time.sleep(6)

print "Total: %d" % (last_stamp - start_stamp)
#
# Add your app code goes here...
#
# When you are done, you could optionally clear the current user. Doing so
# however, means that the next time the script is run, the user will be prompted # noqa
# for his or her credentials again. You should probably avoid doing this in
# order to provide a user experience that is as frictionless as possible.
authenticator.clear_default_user()
