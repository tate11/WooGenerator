from os import sys, path
import random
# import unittest
import traceback
from unittest import main #, skip, TestCase
# from tabulate import tabulate
from bisect import insort

if __name__ == '__main__' and __package__ is None:
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from testSyncClient import abstractSyncClientTestCase
from context import woogenerator
from woogenerator.utils import TimeUtils, Registrar, SanitationUtils
from woogenerator.sync_client_user import UsrSyncClient_WP
from woogenerator.coldata import ColData_User
from woogenerator.csvparse_user import CSVParse_User, CSVParse_User_Api #, ImportUser
from woogenerator.matching import UsernameMatcher, MatchList #, CardMatcher, NocardEmailMatcher, EmailMatcher
from woogenerator.SyncUpdate import SyncUpdate, SyncUpdate_Usr_Api

class testUsrSyncUpdate(abstractSyncClientTestCase):
    yamlPath = "merger_config.yaml"
    optionNamePrefix = 'test_'

    def __init__(self, *args, **kwargs):
        super(testUsrSyncUpdate, self).__init__(*args, **kwargs)
        self.SSHTunnelForwarderParams = {}
        self.PyMySqlConnectParams = {}
        self.jsonConnectParams = {}
        self.actConnectParams = {}
        self.actDbParams = {}
        self.fsParams = {}

    def processConfig(self, config):
        wp_srv_offset = config.get(self.optionNamePrefix+'wp_srv_offset', 0)
        wp_api_key = config.get(self.optionNamePrefix+'wp_api_key')
        wp_api_secret = config.get(self.optionNamePrefix+'wp_api_secret')
        store_url = config.get(self.optionNamePrefix+'store_url', '')
        wp_user = config.get(self.optionNamePrefix+'wp_user')
        wp_pass = config.get(self.optionNamePrefix+'wp_pass')
        wp_callback = config.get(self.optionNamePrefix+'wp_callback')
        merge_mode = config.get('merge_mode', 'sync')
        MASTER_NAME = config.get('master_name', 'MASTER')
        SLAVE_NAME = config.get('slave_name', 'SLAVE')
        DEFAULT_LAST_SYNC = config.get('default_last_sync')

        TimeUtils.setWpSrvOffset(wp_srv_offset)
        SyncUpdate.setGlobals( MASTER_NAME, SLAVE_NAME, merge_mode, DEFAULT_LAST_SYNC)


        self.wpApiParams = {
            'api_key': wp_api_key,
            'api_secret': wp_api_secret,
            'url':store_url,
            'wp_user':wp_user,
            'wp_pass':wp_pass,
            'callback':wp_callback
        }

        # Registrar.DEBUG_UPDATE = True

    def setUp(self):
        super(testUsrSyncUpdate, self).setUp()

        for var in ['wpApiParams']:
            print var, getattr(self, var)

        Registrar.DEBUG_API = True

    def testUploadSlaveChanges(self):

        maParser = CSVParse_User(
            cols=ColData_User.getACTImportCols(),
            defaults=ColData_User.getDefaults()
        )

        master_bus_type = "Salon"
        master_client_grade = str(random.random())
        master_uname = "neil"

        master_data = [map(unicode, row) for row in [
            ["E-mail","Role","First Name","Surname","Nick Name","Contact","Client Grade","Direct Brand","Agent","Birth Date","Mobile Phone","Fax","Company","Address 1","Address 2","City","Postcode","State","Country","Phone","Home Address 1","Home Address 2","Home City","Home Postcode","Home Country","Home State","MYOB Card ID","MYOB Customer Card ID","Web Site","ABN","Business Type","Referred By","Lead Source","Mobile Phone Preferred","Phone Preferred","Personal E-mail","Edited in Act","Wordpress Username","display_name","ID","updated"],
            ["neil@technotan.com.au","ADMIN","Neil","Cunliffe-Williams","Neil Cunliffe-Williams","",master_client_grade,"TT","","",+61416160912,"","Laserphile","7 Grosvenor Road","","Bayswater",6053,"WA","AU","0416160912","7 Grosvenor Road","","Bayswater",6053,"AU","WA","","","http://technotan.com.au",32,master_bus_type,"","","","","","",master_uname,"Neil",1,"2015-07-13 22:33:05"]
        ]]

        maParser.analyseRows(master_data)

        print "MASTER RECORDS: \n", maParser.tabulate()

        saParser = CSVParse_User_Api(
            cols=ColData_User.getWPImportCols(),
            defaults=ColData_User.getDefaults()
        )

        with UsrSyncClient_WP(self.wpApiParams ) as slaveClient:
            slaveClient.analyseRemote(saParser, search=master_uname)

        print "SLAVE RECORDS: \n", saParser.tabulate()

        updates = []
        globalMatches = MatchList()

        # Matching
        usernameMatcher = UsernameMatcher()
        usernameMatcher.processRegisters(saParser.usernames, maParser.usernames)
        globalMatches.addMatches( usernameMatcher.pureMatches)

        print "username matches (%d pure)" % len(usernameMatcher.pureMatches)

        syncCols = ColData_User.getSyncCols()

        for count, match in enumerate(globalMatches):
            mObject = match.mObjects[0]
            sObject = match.sObjects[0]

            syncUpdate = SyncUpdate_Usr_Api(mObject, sObject)
            syncUpdate.update(syncCols)

            print "SyncUpdate: ", syncUpdate.tabulate()

            if not syncUpdate:
                continue

            if syncUpdate.sUpdated:
                insort(updates, syncUpdate)

        slaveFailures = []

        #
        response_json = {}

        with UsrSyncClient_WP(self.wpApiParams) as slaveClient:

            for count, update in enumerate(updates):
                try:
                    response = update.updateSlave(slaveClient)
                    print "response (code) is %s" % response
                    assert response, "response should exist because update should not be empty. update: %s" % update.tabulate(tablefmt="html")
                    if response:
                        print "response text: %s" % response.text
                        response_json = response.json()

                except Exception, e:
                    slaveFailures.append({
                        'update':update,
                        'master':SanitationUtils.coerceUnicode(update.newMObject),
                        'slave':SanitationUtils.coerceUnicode(update.newSObject),
                        'mchanges':SanitationUtils.coerceUnicode(update.getMasterUpdates()),
                        'schanges':SanitationUtils.coerceUnicode(update.getSlaveUpdates()),
                        'exception':repr(e)
                    })
                    Registrar.registerError("ERROR UPDATING SLAVE (%s): %s\n%s" % (
                        update.SlaveID,
                        repr(e),
                        traceback.format_exc()
                    ) )

        self.assertTrue(response_json.get('meta'))
        self.assertEqual(response_json.get('meta', {}).get('business_type'), master_bus_type)
        self.assertEqual(response_json.get('meta', {}).get('client_grade'), master_client_grade)


if __name__ == '__main__':
    main()
