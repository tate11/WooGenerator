"""
Containers and parsers for processing user data
"""

from collections import OrderedDict
from pprint import pformat  # pprint
# from copy import deepcopy

from woogenerator.coldata import ColData_User  # , ColData_Woo
from woogenerator.contact_objects import ContactAddress, ContactName
from woogenerator.contact_objects import ContactPhones, SocialMediaFields
from woogenerator.utils import descriptorUtils, listUtils, SanitationUtils, TimeUtils, Registrar
from woogenerator.parsing.abstract import ObjList
from woogenerator.parsing.flat import ImportFlat, CSVParse_Flat


class UsrObjList(ObjList):
    """
    A list of `ImportUser` objects
    """

    def __init__(self, objects=None, indexer=None):
        super(UsrObjList, self).__init__(objects, indexer=None)
        self._obj_list_type = 'User'

    reportCols = ColData_User.get_report_cols()

    def getSanitizer(self, tablefmt=None):
        if tablefmt is 'html':
            return SanitationUtils.sanitizeForXml
        elif tablefmt is 'simple':
            return SanitationUtils.sanitizeForTable
        else:
            return super(UsrObjList, self).getSanitizer(tablefmt)

    @classmethod
    def get_basic_cols(cls, self):
        return ColData_User.get_basic_cols()


class ImportUser(ImportFlat):
    container = UsrObjList

    wpid = descriptorUtils.safeKeyProperty('Wordpress ID')
    # TODO: does this break anything?
    email = descriptorUtils.safeNormalizedKeyProperty('E-mail')
    # email = descriptorUtils.safeKeyProperty('E-mail')
    MYOBID = descriptorUtils.safeKeyProperty('MYOB Card ID')
    username = descriptorUtils.safeKeyProperty('Wordpress Username')
    role = descriptorUtils.safeKeyProperty('Role')
    # contact_schema = descriptorUtils.safeKeyProperty('contact_schema')
    billing_address = descriptorUtils.safeKeyProperty('Address')
    shipping_address = descriptorUtils.safeKeyProperty('Home Address')
    name = descriptorUtils.safeKeyProperty('Name')

    aliasMapping = {
        'Address':
        ['Address 1', 'Address 2', 'City', 'Postcode', 'State', 'Country'],
        'Home Address': [
            'Home Address 1', 'Home Address 2', 'Home City', 'Home Postcode',
            'Home State', 'Home Country'
        ],
        'Name': [
            'Name Prefix', 'First Name', 'Middle Name', 'Surname',
            'Name Suffix', 'Company', 'Memo', 'Contact'
        ],
        'Phone Numbers': ['Phone', 'Mobile Phone', 'Fax'],
        'Social Media': [
            'Facebook Username',
            'Twitter Username',
            'GooglePlus Username',
            'Instagram Username',
        ],
        #  'Web Site'],
        # 'E-mails': ['E-mail', 'Personal E-mail']
    }

    @property
    def index(self):
        return "%s | %s" % (self.wpid, self.MYOBID)

    @property
    def act_modtime(self):
        time_str = self.get('Edited in Act')
        if time_str:
            return TimeUtils.act_strp_mktime(time_str)

    @property
    def act_created(self):
        time_str = self.get('Create Date')
        if time_str:
            return TimeUtils.act_strp_mktime(time_str)

    @property
    def wp_created(self):
        time_str = self.get('Wordpress Start Date')
        if time_str:
            return TimeUtils.wp_strp_mktime(time_str)

    @property
    def wp_modtime(self):
        time_str = self.get('Edited in Wordpress')
        if time_str:
            return TimeUtils.wp_server_to_local_time(
                TimeUtils.wp_strp_mktime(time_str))

    @property
    def last_sale(self):
        time_str = self.get('Last Sale')
        if time_str:
            return TimeUtils.act_strp_mkdate(time_str)

    @property
    def last_modtime(self):
        times = [
            self.act_modtime, self.wp_modtime, self.act_created,
            self.wp_created, self.last_sale
        ]
        return max(times)

    @property
    def act_last_transaction(self):
        """ effective last sale (if no last sale, use act create date) """
        response = self.last_sale
        if not response:
            response = self.act_created
        assert response, "customer should always have a create (%s) or last sale (%s)" % (
            self.act_created, self.last_sale)
        return response

    def __init__(self, data, **kwargs):
        super(ImportUser, self).__init__(data, **kwargs)
        for key in [
                'E-mail', 'MYOB Card ID', 'Wordpress Username', 'Role',
                'contact_schema', 'Wordpress ID'
        ]:
            val = kwargs.get(key, "")
            if (val):
                self[key] = val
            elif (not self.get(key)):
                self[key] = ""
            if (self.DEBUG_USR):
                self.registerMessage(
                    "key: {key}, value: {val}".format(key=key, val=self[key]))
        if (self.DEBUG_USR):
            self.registerMessage("data:" + repr(data))
        self.initContactObjects(data)

    def initContactObjects(self, data):
        # emails_kwargs = OrderedDict(filter(None, [\
        #     ((key, data.get(value)) if data.get(value) else None) for key, value in\
        #     {
        #         'email'         : 'E-mail',
        #         'personal_email': 'Personal E-mail',
        #     }.items()
        # ]))
        #
        # self['E-mails'] = EmailFields(
        #     **emails_kwargs
        # )

        name_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'first_name': 'First Name',
                'middle_name': 'Middle Name',
                'family_name': 'Surname',
                'name_prefix': 'Name Prefix',
                'name_suffix': 'Name Suffix',
                'contact': 'Contact',
                'company': 'Company',
                'city': 'City',
                'country': 'Country',
                'state': 'State',
            }.items()
        ]))

        self['Name'] = ContactName(**name_kwargs)

        assert self['Name'] is not None, \
            'contact is missing mandatory fields: something went wrong'

        address_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None)
            for key, value in
            {
                'line1': 'Address 1',
                'line2': 'Address 2',
                'city': 'City',
                'postcode': 'Postcode',
                'state': 'State',
                'country': 'Country',
                'company': 'Company',
            }.items()
        ]))

        self['Address'] = ContactAddress(**address_kwargs)

        # print "ADDRESS: ", self['Address']

        alt_address_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'line1': 'Home Address 1',
                'line2': 'Home Address 2',
                'city': 'Home City',
                'postcode': 'Home Postcode',
                'state': 'Home State',
                'country': 'Home Country',
                'company': 'Company',
            }.items()
        ]))

        self['Home Address'] = ContactAddress(**alt_address_kwargs)

        # print "HOME ADDRESS: ", self['Home Address']

        phone_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'mob_number': 'Mobile Phone',
                'tel_number': 'Phone',
                'fax_number': 'Fax',
                'mob_pref': 'Mobile Phone Preferred',
                'tel_pref': 'Phone Preferred',
            }.items()
        ]))

        self['Phone Numbers'] = ContactPhones(**phone_kwargs)

        social_media_kwargs = OrderedDict(filter(None, [
            ((key, data.get(value)) if data.get(value) else None) for key, value in
            {
                'facebook': 'Facebook Username',
                'twitter': 'Twitter Username',
                'gplus': 'GooglePlus Username',
                'instagram': 'Instagram Username',
                'website': 'Web Site',
            }.items()
        ]))

        self['Social Media'] = SocialMediaFields(**social_media_kwargs)

        emails = []
        if data.get('E-mail'):
            emails = listUtils.combineLists(
                emails, SanitationUtils.findallEmails(data['E-mail']))
        if data.get('Personal E-mail'):
            emails = listUtils.combineLists(
                emails,
                SanitationUtils.findallEmails(data.get('Personal E-mail')))
        self['E-mail'] = emails.pop(0) if emails else None
        self['Personal E-mail'] = ', '.join(emails)

        urls = []
        if data.get('Web Site'):
            urls = listUtils.combineLists(
                urls, SanitationUtils.findallURLs(data['Web Site']))
        self['Web Site'] = urls.pop(0) if urls else None

        # if not self['Emails'].valid:
        #     self['emails_reason'] = '\n'.join(filter(None, [
        #         self['Emails'].reason,
        #     ]))

        if not self['Address'].valid or not self['Home Address'].valid:
            self['address_reason'] = '\n'.join(
                filter(None, [
                    'ADDRESS: ' + self['Address'].reason if not self['Address']
                    .valid else None, 'HOME ADDRESS: ' + self['Home Address']
                    .reason if not self['Home Address'].valid else None
                ]))

        if not self['Name'].valid:
            self['name_reason'] = '\n'.join(
                filter(None, [
                    self['Name'].reason,
                ]))

        if not self['Phone Numbers'].valid:
            self['phone_reason'] = '\n'.join(
                filter(None, [
                    self['Phone Numbers'].reason,
                ]))

        if not self['Social Media'].valid:
            self['social_reason'] = '\n'.join(
                filter(None, [
                    self['Social Media'].reason,
                ]))

    def refreshContactObjects(self):
        pass
        # self.initContactObjects(self.__getstate__())

    def __getitem__(self, key):
        for alias, keys in self.aliasMapping.items():
            if key in keys and alias in self:
                return self[alias][key]
        return super(ImportUser, self).__getitem__(key)

    def __setitem__(self, key, val):
        # print "setting obj %s to %s " % (key, repr(val))
        for alias, keys in self.aliasMapping.items():
            if key in keys and alias in self:
                self[alias][key] = val
                return
        # if key is 'Name': print "setting Name to ", val
        super(ImportUser, self).__setitem__(key, val)
        # if key is 'Name':

    # print self.__getitem__(key)

    def get(self, key, default=None):
        for alias, keys in self.aliasMapping.items():
            if key in keys and self[alias]:
                return self[alias][key]
        try:
            return super(ImportUser, self).get(key, default)
        except:
            return None

    @staticmethod
    def getNewObjContainer():
        return UsrObjList

    def addressesActLike(self):
        act_like = True
        for address in filter(None,
                              map(lambda key: self.get(key),
                                  ['Address', 'Home Address'])):
            if address.schema and address.schema != 'act':
                act_like = False
        return act_like

    def usernameActLike(self):
        return self.username == self.MYOBID

    def __repr__(self):
        return "<%s> %s | %s | %s | %s | %s" % (
            self.index, self.email, self.MYOBID, self.role, self.username,
            self.wpid)


class CSVParse_User(CSVParse_Flat):

    objectContainer = ImportUser

    def __init__(self,
                 cols=[],
                 defaults={},
                 contact_schema=None,
                 filterItems=None,
                 limit=None,
                 source=None):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        extra_cols = [
            # 'ABN', 'Added to mailing list', 'Address 1', 'Address 2', 'Agent', 'Birth Date',
            # 'book_spray_tan', 'Book-a-Tan Expiry', 'Business Type', 'Canvasser', ''
            # 'post_status'
        ]
        extra_defaults = OrderedDict([
            # ('post_status', 'publish'),
            # ('last_import', import_name),
        ])
        cols = listUtils.combineLists(cols, extra_cols)
        defaults = listUtils.combineOrderedDicts(defaults, extra_defaults)
        super(CSVParse_User, self).__init__(
            cols, defaults, limit=limit, source=source)
        self.contact_schema = contact_schema
        self.filterItems = filterItems
        # self.itemIndexer = self.getUsername

    # def getKwargs(self, all_data, container, **kwargs):
    #     kwargs = super(CSVParse_User, self).getKwargs(all_data, container, **kwargs)
    #     for key in ['E-mail', 'MYOB Card ID', 'username', 'Role']:
    #         assert kwargs[key] is not None
    #     return kwargs

    # def newObject(self, rowcount, row, **kwargs):
    #     for key in ['E-mail', 'MYOB Card ID', 'username', 'Role']:
    #         try:
    #             assert kwargs[key]
    #         except:
    #             kwargs[key] = self.retrieveColFromRow

    def clearTransients(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(CSVParse_User, self).clearTransients()
        self.roles = OrderedDict()
        self.noroles = OrderedDict()
        self.emails = OrderedDict()
        self.noemails = OrderedDict()
        self.cards = OrderedDict()
        self.nocards = OrderedDict()
        self.usernames = OrderedDict()
        self.nousernames = OrderedDict()
        # self.companies = OrderedDict()
        self.addresses = OrderedDict()
        self.filtered = OrderedDict()
        self.bad_name = OrderedDict()
        self.bad_address = OrderedDict()
        # self.badEmail = OrderedDict()

    def sanitizeCell(self, cell):
        return SanitationUtils.sanitizeCell(cell)

    def registerEmail(self, object_data, email):
        # TODO: does this line break anything?
        email = SanitationUtils.normalize_val(email)
        self.registerAnything(
            object_data,
            self.emails,
            email,
            singular=False,
            registerName='emails')

    def registerNoEmail(self, object_data):
        self.registerAnything(
            object_data,
            self.noemails,
            object_data.index,
            singular=True,
            registerName='noemails')

    def registerRole(self, object_data, role):
        self.registerAnything(
            object_data, self.roles, role, singular=False, registerName='roles')

    def registerNoRole(self, object_data):
        self.registerAnything(
            object_data,
            self.noroles,
            object_data.index,
            singular=True,
            registerName='noroles')

    def registerCard(self, object_data, card):
        self.registerAnything(
            object_data, self.cards, card, singular=False, registerName='cards')

    def registerNoCard(self, object_data):
        self.registerAnything(
            object_data,
            self.nocards,
            object_data.index,
            singular=True,
            registerName='nocards')

    def registerUsername(self, object_data, username):
        self.registerAnything(
            object_data,
            self.usernames,
            username,
            singular=False,
            registerName='usernames')

    def registerNoUsername(self, object_data):
        self.registerAnything(
            object_data,
            self.nousernames,
            object_data.index,
            singular=True,
            registerName='nousernames')

    # def registerCompany(self, object_data, company):
    #     self.registerAnything(
    #         object_data,
    #         self.companies,
    #         company,
    #         singular = False,
    #         registerName = 'companies'
    #     )

    def registerFiltered(self, object_data):
        self.registerAnything(
            object_data,
            self.filtered,
            object_data.index,
            singular=True,
            registerName='filtered')

    def registerBadAddress(self, object_data, address):
        self.registerAnything(
            object_data,
            self.bad_address,
            object_data.index,
            singular=True,
            registerName='badaddress')

    def registerBadName(self, object_data, name):
        self.registerAnything(
            object_data,
            self.bad_name,
            object_data.index,
            singular=True,
            registerName='badname')

    # def registerBadEmail(self, object_data, name):
    #     self.registerAnything(
    #         object_data,
    #         self.badEmail,
    #         object_data.index,
    #         singular = True,
    #         registerName = 'bademail'
    #     )

    def registerAddress(self, object_data, address):
        address_str = str(address)
        if address_str:
            self.registerAnything(
                object_data,
                self.addresses,
                address_str,
                singular=False,
                registerName='address')

    def validateFilters(self, object_data):
        if self.filterItems:
            if 'roles' in self.filterItems.keys(
            ) and object_data.role not in self.filterItems['roles']:
                if self.DEBUG_USR:
                    self.registerMessage(
                        "could not register object %s because did not match role"
                        % object_data.__repr__())
                return False
            if 'sinceM' in self.filterItems.keys(
            ) and object_data.act_modtime < self.filterItems['sinceM']:
                if self.DEBUG_USR:
                    self.registerMessage(
                        "could not register object %s because did not meet sinceM condition"
                        % object_data.__repr__())
                return False
            if 'sinceS' in self.filterItems.keys(
            ) and object_data.wp_modtime < self.filterItems['sinceS']:
                if self.DEBUG_USR:
                    self.registerMessage(
                        "could not register object %s because did not meet sinceS condition"
                        % object_data.__repr__())
                return False
            if object_data.username in self.filterItems.get('users', []):
                return True
            if object_data.MYOBID in self.filterItems.get('cards', []):
                return True
            if object_data.email in self.filterItems.get('emails', []):
                return True
            if self.DEBUG_USR:
                self.registerMessage(
                    "could not register object %s because did not meet users, cards or emails conditions"
                    % object_data.__repr__())
            return False
        else:
            return True

    def registerObject(self, object_data):
        if not self.validateFilters(object_data):
            self.registerFiltered(object_data)
            return

        email = object_data.email
        if email and SanitationUtils.stringIsEmail(email):
            self.registerEmail(object_data, email)
        else:
            if (self.DEBUG_USR):
                self.registerWarning("invalid email address: %s" % email)
            self.registerNoEmail(object_data)

        role = object_data.role
        if role:
            self.registerRole(object_data, role)
        else:
            # self.registerWarning("invalid role: %s"%role)
            self.registerNoRole(object_data)

        card = object_data.MYOBID
        if card and SanitationUtils.stringIsMYOBID(card):
            self.registerCard(object_data, card)
        else:
            self.registerNoCard(object_data)

        username = object_data.username
        if username:
            self.registerUsername(object_data, username)
        else:
            if (self.DEBUG_USR):
                self.registerWarning("invalid username: %s" % username)
            self.registerNoUsername(object_data)

        # company = object_data['Company']
        # # if self.DEBUG_USR: SanitationUtils.safePrint(repr(object_data), company)
        # if company:
        #     self.registerCompany(object_data, company)

        addresses = [object_data.billing_address, object_data.shipping_address]
        for address in filter(None, addresses):
            if not address.valid:
                reason = address.reason
                assert reason, "there must be a reason that this address is invalid: " + address
                self.registerBadAddress(object_data, address)
            else:
                self.registerAddress(object_data, address)

        name = object_data.name
        # print "NAME OF %s IS %s" % (repr(object_data),
        # name.__str__(out_schema="flat"))
        if not name.valid:
            reason = name.reason
            assert reason, "there must be a reason that this name is invalid: " + name
            # print "registering bad name: ", SanitationUtils.coerceBytes(name)
            self.registerBadName(object_data, name)

        # emails = object_data.emails
        # if not emails.valid:
        #     reason = emails.reason
        #     self.registerBadEmail(object_data, emails)

        super(CSVParse_User, self).registerObject(object_data)

    def getKwargs(self, all_data, container, **kwargs):
        kwargs = super(CSVParse_User, self).getKwargs(all_data, container, **
                                                      kwargs)
        if not 'contact_schema' in kwargs.keys():
            kwargs['contact_schema'] = self.contact_schema
        return kwargs

    # def processRoles(self, object_data):
    #     role = object_data.role
    #     if not self.roles.get(role): self.roles[role] = OrderedDict()
    #     self.registerAnything(
    #         object_data,
    #         self.roles[role],
    #         self.getUsername,
    #         singular = True,
    #         registerName = 'roles'
    #     )

    # def processObject(self, object_data):
    #     # object_data.username = self.getMYOBID(object_data)
    #     super(CSVParse_Flat, self).processObject(object_data)
    #     self.processRoles(object_data)

    # def analyzeRow(self, row, object_data):
    #     object_data = super(CSVParse_Flat, self).analyseRow(row, object_data)
    #     return object_data


class CSVParse_User_Api(CSVParse_User):

    @classmethod
    def getParserData(cls, **kwargs):
        """
        Gets data ready for the parser, in this case from api_data
        """
        parser_data = OrderedDict()
        api_data = kwargs.get('api_data', {})
        print "api_data before: %s" % str(api_data)
        api_data = dict([(key, SanitationUtils.html_unescape_recursive(value))
                        for key, value in api_data.items()])
        print "api_data after:  %s" % str(api_data)
        parser_data = OrderedDict()
        core_translation = OrderedDict()
        for col, col_data in ColData_User.get_wpapi_core_cols().items():
            try:
                wp_api_key = col_data['wp-api']['key']
            except:
                wp_api_key = col
            core_translation[wp_api_key] = col
        if Registrar.DEBUG_API:
            Registrar.registerMessage("core_translation: %s" %
                                      pformat(core_translation))
        parser_data.update(**cls.translateKeys(api_data, core_translation))

        if 'meta' in api_data:
            meta_translation = OrderedDict()
            meta_data = api_data['meta']
            # if Registrar.DEBUG_API: Registrar.registerMessage("meta data: %s" % pformat(ColData_User.getWPAPIMetaCols().items()))
            for col, col_data in ColData_User.getWPAPIMetaCols().items():
                try:
                    if 'wp-api' in col_data:
                        wp_api_key = col_data['wp-api']['key']
                    elif 'wp' in col_data:
                        wp_api_key = col_data['wp']['key']
                except Exception:
                    wp_api_key = col

                meta_translation[wp_api_key] = col
            if Registrar.DEBUG_API:
                Registrar.registerMessage("meta_translation: %s" %
                                          pformat(meta_translation))
            meta_translation_result = cls.translateKeys(meta_data,
                                                        meta_translation)
            # if Registrar.DEBUG_API: Registrar.registerMessage("meta_translation_result: %s" % pformat(meta_translation_result))
            parser_data.update(**meta_translation_result)

        if Registrar.DEBUG_API:
            Registrar.registerMessage(
                "parser_data: {}".format(pformat(parser_data)))
        return parser_data

    def analyseWpApiObj(self, api_data):
        kwargs = {'api_data': api_data}
        object_data = self.newObject(rowcount=self.rowcount, **kwargs)
        if self.DEBUG_API:
            self.registerMessage("CONSTRUCTED: %s" % object_data.identifier)
        self.processObject(object_data)
        if self.DEBUG_API:
            self.registerMessage("PROCESSED: %s" % object_data.identifier)
        self.registerObject(object_data)
        if self.DEBUG_API:
            self.registerMessage("REGISTERED: %s" % object_data.identifier)
        # self.registerMessage("mro: {}".format(container.mro()))
        self.rowcount += 1
