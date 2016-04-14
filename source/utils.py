# -*- coding: utf-8 -*-
import functools
import itertools
# from itertools import chain
import re
import time
# import datetime
import inspect
import json
from collections import OrderedDict
import codecs
import csv
import cStringIO
from uniqid import uniqid
from phpserialize import dumps, loads
from kitchen.text import converters
import io
import base64

DEFAULT_ENCODING = 'utf8'

DEBUG = False
DEBUG_ADDRESS = False

class SanitationUtils:
    email_regex = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"
    punctuationChars = [
        '!', '"', '#', '$', '%', '&', '\'', '(', ')', '*', '+', ',', '\-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\\\', '\\]', '^', '_', '`', '{', '|', '}', '~' 
    ]
    myobid_regex = r"C\d+"

    @staticmethod
    def compose(*functions):
        return functools.reduce(lambda f, g: lambda x: f(g(x)), functions)

    # Functions for dealing with string encodings

    @staticmethod
    def unicodeToUTF8(u_str):
        return converters.to_bytes(u_str, "utf8")

    @staticmethod
    def unicodeToAscii(u_str):
        return converters.to_bytes(u_str, "ascii", "backslashreplace")

    @staticmethod
    def unicodeToXml(u_str, ascii_only = False):
        if ascii_only:
            return converters.unicode_to_xml(u_str, encoding="ascii")
        else:
            return converters.unicode_to_xml(u_str)

    @staticmethod
    def utf8ToUnicode(utf8_str):
        return converters.to_unicode(utf8_str, "utf8")

    @staticmethod
    def xmlToUnicode(utf8_str):
        return converters.xml_to_unicode(utf8_str)

    @staticmethod
    def asciiToUnicode(ascii_str):
        return converters.to_unicode(ascii_str, "ascii")

    @staticmethod
    def coerceUnicode(thing):
        if thing is None:
            return u""
        else:
            return converters.to_unicode(thing, encoding="utf8")

    @staticmethod
    def coerceBytes(thing):
        return SanitationUtils.compose(
            SanitationUtils.unicodeToUTF8,
            SanitationUtils.coerceUnicode
        )(thing)

    @staticmethod
    def coerceAscii(thing):
        return SanitationUtils.compose(
            SanitationUtils.unicodeToAscii,
            SanitationUtils.coerceUnicode
        )(thing)

    @staticmethod
    def coerceXML(thing):
        return SanitationUtils.compose(
            SanitationUtils.unicodeToXml,
            SanitationUtils.coerceUnicode
        )(thing)

    @staticmethod
    def sanitizeForTable(thing):
        return SanitationUtils.compose(
            SanitationUtils.escapeNewlines,
            SanitationUtils.coerceUnicode
        )(thing)

    @staticmethod
    def sanitizeForXml(thing):
        return SanitationUtils.compose(
            SanitationUtils.sanitizeNewlines,
            SanitationUtils.unicodeToXml,
            SanitationUtils.coerceUnicode
        )(thing)

    # @staticmethod
    # def anythingToAscii(thing):
    #     if isinstance(thing, unicode):
    #         string = thing.encode(DEFAULT_ENCODING)
    #     elif thing is None:
    #         string = ""
    #     else:
    #         string = str(thing)
    #     return string.encode('ascii', 'backslashreplace')

    # @staticmethod
    # def byteToUnicode(string):
    #     # print unicode(string).encode('ascii','backslashreplace')

    #     if(not isinstance(string, str)):
    #         if isinstance(string, unicode):
    #             return string
    #         else:
    #             string = str(string)
    #         # string = str(string).dec
    #     str_out = string.decode(DEFAULT_ENCODING)
    #     if DEBUG: print "byteToUnicode", repr(string), repr(str_out)
    #     return str_out

    # @staticmethod
    # def unicodeToByte(string):
    #     if(not isinstance(string, unicode)):
    #         if(isinstance(string, str)):
    #             string = string.decode(DEFAULT_ENCODING)
    #         else:
    #             string = unicode(string)
    #     str_out = string.encode('ascii', 'backslashreplace')
    #     if DEBUG: print "unicodeToByte", repr(string), repr(str_out)
    #     return str_out

    # @staticmethod
    # def anythingToUnicode(thing):
    #     if isinstance(thing, unicode):
    #         return thing
    #     elif not isinstance(thing, str):
    #         string = str(thing)

    # @staticmethod
    # def decodeStringEscape(string):
    #     str_out = string.decode('string_escape')
    #     if DEBUG: print "decodeStringEscape", repr(string), repr(str_out)
    #     return str_out


    # @staticmethod
    # def makeSafeOutput(string):
    #     return SanitationUtils.compose(
    #         SanitationUtils.sanitizeNewlines,
    #         SanitationUtils.anythingToAscii
    #     )(string)

    # @staticmethod
    # def makeSafeHTMLOutput(string):
    #     return SanitationUtils.compose(
    #         SanitationUtils.sanitizeNewlines,
    #         SanitationUtils.cleanXMLString,
    #         SanitationUtils.makeUnicodeCSVSafe
    #     )(string)

    # @staticmethod
    # def decodeSafeOutput(string):
    #     return SanitationUtils.compose(
    #         # SanitationUtils.byteToUnicode,
    #         SanitationUtils.asciiToUnicode
    #     )(string)

    # @staticmethod
    # def makeUnicodeCSVSafe(thing):
    #     if thing is None:
    #         return ""
    #     else:
    #         return unicode(thing)


    # @staticmethod
    # def cleanBackslashString(string):
    #     if string is None:
    #         return None
    #     elif isinstance(string, unicode):
    #         unicode_content = string
    #     else:
    #         unicode_content = str(string).decode('utf-8', 'ignore')
    #         assert isinstance(unicode_content, unicode)
    #     backslashed = unicode_content.encode('ascii', 'backslashreplace')
    #     # print "backslashed: ", backslashed
    #     return backslashed

    # @staticmethod
    # def cleanXMLString(string):
    #     # print "cleaning string ", string
    #     if string is None:
    #         return None
    #     elif isinstance(string, unicode):
    #         unicode_content = string
    #     else:
    #         unicode_content = str(string).decode('utf-8', 'ignore')
    #         assert isinstance(unicode_content, unicode)
    #     # print "unicode_content: ", unicode_content
    #     xml_content = unicode_content.encode('ascii', 'xmlcharrefreplace')
    #     # print "xml_content: ", xml_content
    #     return xml_content


    @staticmethod
    def removeLeadingDollarWhiteSpace(string):
        str_out = re.sub('^\W*\$','', string)
        if DEBUG: print "removeLeadingDollarWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLeadingPercentWhiteSpace(string):
        str_out = re.sub('%\W*$','', string)
        if DEBUG: print "removeLeadingPercentWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLoneDashes(string):
        str_out = re.sub('^-$', '', string)
        if DEBUG: print "removeLoneDashes", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeThousandsSeparator(string):
        str_out = re.sub(r'(\d+),(\d{3})', '\g<1>\g<2>', string)
        if DEBUG: print "removeThousandsSeparator", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeLoneWhiteSpace(string):
        str_out = re.sub(r'^\s*$','', string)    
        if DEBUG: print "removeLoneWhiteSpace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def removeNULL(string):
        str_out = re.sub(r'^NULL$', '', string)
        if DEBUG: print "removeNULL", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripLeadingWhitespace(string):
        str_out = re.sub(r'^\s*', '', string)
        if DEBUG: print "stripLeadingWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripTailingWhitespace(string):
        str_out = re.sub(r'\s*$', '', string)
        if DEBUG: print "stripTailingWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripAllWhitespace(string):
        if DEBUG: print "stripAllWhitespace", repr(string)
        str_out = re.sub(r'\s', '', string)
        if DEBUG: print "stripAllWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripExtraWhitespace(string):
        str_out = re.sub(r'\s{2,}', ' ', string)
        if DEBUG: print "stripExtraWhitespace", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripNonNumbers(string):
        str_out = re.sub('[^\d]', '', string)
        if DEBUG: print "stripNonNumbers", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripPunctuation(string):
        str_out = re.sub('[%s]' % ''.join(SanitationUtils.punctuationChars) , '', string)
        if DEBUG: print "stripPunctuation", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def stripAreaCode(string):
        str_out = re.sub('\s*\+\d{2,3}\s*','', string)
        if DEBUG: print "stripAreaCode", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def toLower(string):
        str_out = string.lower()
        if DEBUG: print "toLower", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def toUpper(string):
        str_out = string.upper()
        if DEBUG: print "toUpper", repr(string), repr(str_out)
        return str_out

    @staticmethod
    def sanitizeNewlines(string):
        return re.sub('\n','</br>', string)

    @staticmethod
    def escapeNewlines(string):
        return re.sub('\n','\\n', string)

    @staticmethod
    def compileRegex(subs):
        if subs:
            return re.compile( "(%s)" % '|'.join(filter(None, map(re.escape, subs))) )
        else:
            return None

    @staticmethod
    def sanitizeCell(cell):
        return SanitationUtils.compose(
            SanitationUtils.removeLeadingDollarWhiteSpace,
            SanitationUtils.removeLeadingPercentWhiteSpace,
            SanitationUtils.removeLoneDashes,
            SanitationUtils.removeThousandsSeparator,
            SanitationUtils.removeLoneWhiteSpace,
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,            
            SanitationUtils.sanitizeNewlines,
            SanitationUtils.removeNULL,
            SanitationUtils.coerceUnicode
        )(cell)   

    @staticmethod
    def sanitizeClass(string):
        return re.sub('[^a-z]', '', string.lower())

    @staticmethod
    def similarComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.toLower,
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,
            SanitationUtils.coerceUnicode
        )(string)

    @staticmethod
    def similarPhoneComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.stripNonNumbers,
            SanitationUtils.stripAreaCode,
            SanitationUtils.coerceUnicode
        )(string)

    @staticmethod
    def similarTruStrComparison(string):
        return SanitationUtils.compose(
            SanitationUtils.truishStringToBool,
            SanitationUtils.similarComparison
        )(string)

    @staticmethod
    def makeSafeClass(string):
        return SanitationUtils.compose(
            SanitationUtils.stripAllWhitespace,
            SanitationUtils.stripPunctuation
        )(string)

    @staticmethod
    def shorten(reg, subs, str_in):
        # if(DEBUG_GEN):
        #     print "calling shorten"
        #     print " | reg:", reg
        #     print " | subs:", subs
            # print " | str_i: ",str_in
        if not all([reg, subs, str_in]):
            str_out = str_in
        else:
            str_out = reg.sub(
                lambda mo: subs[mo.string[mo.start():mo.end()]],
                str_in
            )
        # if DEBUG_GEN: 
        #     print " | str_o: ",str_out
        return str_out

    @staticmethod
    def findAllImages(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r'\s*([^.|]*\.[^.|\s]*)(?:\s*|\s*)',instring)

    @staticmethod
    def findAllTokens(instring, delim = "|"):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r'\s*(\b[^\s.|]+\b)\s*', instring )

    @staticmethod
    def findallDollars(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r"\s*\$([\d,]+\.?\d*)", instring)

    @staticmethod
    def findallPercent(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        return re.findall(r"\s*(\d+\.?\d*)%", instring)

    @staticmethod
    def titleSplitter(instring):
        assert isinstance(instring, (str, unicode)), "param must be a string not %s"% type(instring)
        if not isinstance(instring, unicode):
            instring = instring.decode('utf-8')
        found = re.findall(r"^\s*(.*?)\s+[^\s\w&\(\)]\s+(.*?)\s*$", instring)
        if found:
            return found[0]
        else:
            return instring, ""


    @staticmethod
    def stringIsEmail(email):
        return re.match(SanitationUtils.email_regex, email)

    @staticmethod
    def stringIsMYOBID(card):
        return re.match(SanitationUtils.myobid_regex, card)

    @staticmethod
    def stringCapitalized(string):
        return unicode(string) == unicode(string).upper()

    @staticmethod
    def stringContainsNumbers(string):
        if(re.search('\d', string)):
            return True
        else:
            return False

    @staticmethod
    def stringContainsNoNumbers(string):
        return not SanitationUtils.stringContainsNumbers(string)

    @staticmethod
    def truishStringToBool(string):
        if( not string or 'n' in string or 'false' in string or string == '0' or string == 0):
            if DEBUG: print "truishStringToBool", repr(string), 'FALSE'
            return "FALSE"
        else:
            if DEBUG: print "truishStringToBool", repr(string), 'TRUE'
            return "TRUE"

    @staticmethod
    def datetotimestamp(datestring):
        raise DeprecationWarning()
        # assert isinstance(datestring, (str,unicode)), "param must be a string not %s"% type(datestring)
        # return int(time.mktime(datetime.datetime.strptime(datestring, "%d/%m/%Y").timetuple()))    

    @staticmethod
    def decodeJSON(json_str):
        assert isinstance(json_str, (str, unicode))
        attrs = json.loads(json_str)
        return attrs

    @staticmethod
    def encodeJSON(obj):
        assert isinstance(obj, (dict, list))
        json_str = json.dumps(obj, encoding="utf8", ensure_ascii=False)
        return json_str

    @staticmethod
    def encodeBase64(str):
        utf8_str = SanitationUtils.coerceBytes(str)
        return base64.encodestring(utf8_str)

    @staticmethod
    def decodeBase64(b64_str):
        return base64.decodestring(b64_str)



def testSanitationUtils():
    # pass

    obj = {
        'key': SanitationUtils.coerceBytes(" 👌 ashdfk"),
        'list': [
            "🐸",
            u"\u2014"
        ]
    }
    print obj, repr(obj)
    obj_json = SanitationUtils.encodeJSON(obj)
    print SanitationUtils.coerceBytes(obj_json), repr(obj_json)
    obj_json_base64 = SanitationUtils.encodeBase64(obj_json)
    print obj_json_base64
    obj_json_decoded = SanitationUtils.decodeBase64(obj_json_base64)
    print obj_json_decoded
    obj_decoded = SanitationUtils.decodeJSON(obj_json_decoded)
    print obj_decoded

    # n1 = u"D\u00C8RWENT"
    # n2 = u"d\u00E8rwent"
    # print SanitationUtils.unicodeToByte(n1) , \
    #     SanitationUtils.unicodeToByte(SanitationUtils.similarComparison(n1)), \
    #     SanitationUtils.unicodeToByte(n2), \
    #     SanitationUtils.unicodeToByte(SanitationUtils.similarComparison(n2))

    # p1 = "+61 04 3190 8778"
    # p2 = "04 3190 8778"
    # p3 = "+61 (08) 93848512"
    # print \
    #     SanitationUtils.similarPhoneComparison(p1), \
    #     SanitationUtils.similarPhoneComparison(p2), \
    #     SanitationUtils.similarPhoneComparison(p3)

    # print SanitationUtils.makeSafeOutput(u"asdad \u00C3 <br> \n \b")

    # tru = SanitationUtils.similarComparison(u"TRUE")

    # print \
    #     SanitationUtils.similarTruStrComparison('yes'), \
    #     SanitationUtils.similarTruStrComparison('no'), \
    #     SanitationUtils.similarTruStrComparison('TRUE'),\
    #     SanitationUtils.similarTruStrComparison('FALSE'),\
    #     SanitationUtils.similarTruStrComparison(0),\
    #     SanitationUtils.similarTruStrComparison('0'),\
    #     SanitationUtils.similarTruStrComparison(u"0")\
        # a = u'TechnoTan Roll Up Banner Insert \u2014 Non personalised - Style D'
    # print 'a', repr(a)
    # b = SanitationUtils.makeSafeOutput(a)
    # print 'b', repr(b)
    # b = SanitationUtils.makeSafeHTMLOutput(u"T\u00C8A GRAHAM\nYEAH")
    # print 'b', b, repr(b)
    # c = SanitationUtils.makeSafeHTMLOutput(None)
    # print 'c', c, repr(c)
    # print SanitationUtils.makeSafeOutput(None)
    # c = SanitationUtils.decodeSafeOutput(b)
    # print 'c', repr(c)

class ValidationUtils:
    @staticmethod
    def isNotNone(arg):
        return arg is not None

    @staticmethod
    def isContainedIn(l):
        return lambda v: v in l

class PHPUtils:
    @staticmethod
    def uniqid(prefix="", more_entropy=False):
        return uniqid(prefix, more_entropy)

    @staticmethod
    def ruleset_uniqid():
        return PHPUtils.uniqid("set_")

    @staticmethod
    def serialize(thing):
        return dumps(thing)

    @staticmethod
    def unserialize(string):
        return loads(string)


def compilePartialAbbrvRegex( abbrvKey, abbrvs ):
    return "|".join(filter(None,[
        "|".join(filter(None,abbrvs)),
        abbrvKey
    ]))

def compileAbbrvRegex( abbrv ):
    return "|".join(filter(None,
        [compilePartialAbbrvRegex(abbrvKey, abbrvValue) for abbrvKey, abbrvValue in abbrv.items()]
    ))


class AddressUtils:
    subunitAbbreviations = OrderedDict([
        # ('ANT',     ['ANTENNA']),
        ('APT',     ['APARTMENT', 'A']),
        # ('ATM',     ['AUTOMATED TELLER MACHINE']),
        ('BBQ',     ['BARBECUE']),
        # ('BTSD',    ['BOATSHED']),
        ('BLDG',    ['BUILDING']),
        # ('BNGW',    ['BUNGALOW']),
        # ('CAGE',    []),
        # ('CARP',    ['CARPARK']),
        # ('CARS',    ['CARSPACE']),
        # ('CLUB',    []),
        # ('COOL',    ['COOLROOM']),
        # ('CTGE',    ['COTTAGE']),
        ('DUPL',    ['DUPLEX']),
        ('FCTY',    ['FACTORY', 'FY']),
        ('FLAT',    ['FLT','FL','F']),
        ('GRGE',    ['GARAGE']),
        ('HALL',    []),
        ('HSE',     ['HOUSE']),
        ('KSK',     ['KIOSK']),
        ('LSE',     ['LEASE']),
        ('LBBY',    ['LOBBY']),
        ('LOFT',    []),
        ('LOT',     []),
        # ('MSNT',    ['MAISONETTE']),
        # ('MBTH',    ['MARINE BERTH', 'MB']),
        ('OFFC',    ['OFFICE', 'OFF']),
        # ('RESV',    ['RESERVE']),
        ('ROOM',    ['RM']),
        ('SHED',    []),
        ('SHOP',    ['SH', 'SP']),
        ('SHRM',    ['SHOWROOM']),
        # ('SIGN',    []),
        ('SITE',    []),
        ('STLL',    ['STALL', 'SL']),
        ('STOR',    ['STORE']),
        ('STR',     ['STRATA UNIT']),
        ('STU',     ['STUDIO', 'STUDIO APARTMENT']),
        ('SUBS',    ['SUBSTATION']),
        ('SE',      ['SUITE']),
        ('TNCY',    ['TENANCY']),
        ('TWR',     ['TOWER']),
        ('TNHS',    ['TOWNHOUSE']),
        ('UNIT',    ['U']),
        ('VLT',     ['VAULT']),
        ('VLLA',    ['VILLA']),
        ('WARD',    []),
        ('WHSE',    ['WAREHOUSE', 'WE']),
        ('WKSH',    ['WORKSHOP'])
    ])

    stateAbbreviations = OrderedDict([
        ('WA',      ['WESTERN AUSTRALIA', 'WEST AUSTRALIA', 'WEST AUS']),
        ('ACT',     ['AUSTRALIAN CAPITAL TERRITORY', 'AUS CAPITAL TERRITORY']),
        ('NSW',     ['NEW SOUTH WALES']),
        ('NT',      ['NORTHERN TERRITORY']),
        ('QLD',     ['QUEENSLAND']),
        ('SA',      ['SOUTH AUSTRALIA']),
        ('TAS',     ['TASMAIA'])
    ])

    floorAbbreviations = OrderedDict([
        ('B',       ['BASEMENT']),
        ('G',       ['GROUND FLOOR', 'GROUND']),
        ('LG',      ['LOWER GROUND FLOOR', 'LOWER GROUND']),
        ('UG',      ['UPPER GROUND FLOOR', 'UPPER GROUND']),
        ('FL',      ['FLOOR', 'FLR']),
        ('LVL',       ['LEVEL', 'L']),
        ('M',       ['MEZZANINE', 'MEZ'])
    ])

    thoroughfareTypeAbbreviations = OrderedDict([
        ('ACCS',     ['ACCESS']),
        ('ALLY',     ['ALLEY']),
        ('ALWY',     ['ALLEYWAY']),
        ('AMBL',     ['AMBLE']),
        ('APP',      ['APPROACH']),
        ('ARC',      ['ARCADE']),
        ('ARTL',     ['ARTERIAL']),
        ('ARTY',     ['ARTERY']),
        ('AVE',      ['AVENUE','AV']),
        ('BA',       ['BANAN']),
        ('BEND',     []),
        ('BWLK',     ['BOARDWALK']),
        ('BLVD',      ['BOULEVARD', 'BLVD']),
        ('BR',       ['BRACE']),
        ('BRAE',     []),
        ('BRK',      ['BREAK']),
        ('BROW',     []),
        ('BYPA',     ['BYPASS']),
        ('BYWY',     ['BYWAY']),
        ('CSWY',     ['CAUSEWAY']),
        ('CTR',      ['CENTRE']),
        ('CH',       ['CHASE']),
        ('CIR',      ['CIRCLE']),
        ('CCT',      ['CIRCUIT']),
        ('CRCS',     ['CIRCUS']),
        ('CL',       ['CLOSE']),
        ('CON',      ['CONCOURSE']),
        ('CPS',      ['COPSE']),
        ('CNR',      ['CORNER']),
        ('CT',       ['COURT']),
        ('CTYD',     ['COURTYARD']),
        ('COVE',     []),
        ('CRES',     ['CRESCENT', 'CR', 'CRESENT']),
        ('CRST',     ['CREST']),
        ('CRSS',     ['CROSS']),
        ('CSAC',     ['CUL-DE-SAC']),
        ('CUTT',     ['CUTTING']),
        ('DALE',     []),
        ('DIP',      []),
        ('DR',       ['DRIVE']),
        ('DVWY',     ['DRIVEWAY']),
        ('EDGE',     []),
        ('ELB',      ['ELBOW']),
        ('END',      []),
        ('ENT',      ['ENTRANCE']),
        ('ESP',      ['ESPLANADE']),
        ('EXP',      ['EXPRESSWAY']),
        ('FAWY',     ['FAIRWAY']),
        ('FOLW',     ['FOLLOW']),
        ('FTWY',     ['FOOTWAY']),
        ('FORM',     ['FORMATION']),
        ('FWY',      ['FREEWAY']),
        ('FRTG',     ['FRONTAGE']),
        ('GAP',      []),
        ('GDNS',     ['GARDENS']),
        ('GTE',      ['GATE']),
        ('GLDE',     ['GLADE']),
        ('GLEN',     []),
        ('GRA',      ['GRANGE']),
        ('GRN',      ['GREEN']),
        ('GR',       ['GROVE']),
        ('HTS',      ['HEIGHTS']),
        ('HIRD',     ['HIGHROAD']),
        ('HWY',      ['HIGHWAY']),
        ('HILL',     []),
        ('INTG',     ['INTERCHANGE']),
        ('JNC',      ['JUNCTION']),
        ('KEY',      []),
        ('LANE',     []),
        ('LNWY',     ['LANEWAY']),
        ('LINE',     []),
        ('LINK',     []),
        ('LKT',      ['LOOKOUT']),
        ('LOOP',     []),
        ('MALL',     []),
        ('MNDR',     ['MEANDER']),
        ('MEWS',     []),
        ('MTWY',     ['MOTORWAY']),
        ('NOOK',     []),
        ('OTLK',     ['OUTLOOK']),
        ('PDE',      ['PARADE']),
        ('PWY',      ['PARKWAY']),
        ('PASS',     []),
        ('PSGE',     ['PASSAGE']),
        ('PATH',     []),
        ('PWAY',     ['PATHWAY']),
        ('PIAZ',     ['PIAZZA']),
        ('PL',       ['PLACE', 'PLCE']),
        ('PLZA',     ['PLAZA']),
        ('PKT',      ['POCKET']),
        ('PNT',      ['POINT']),
        ('PORT',     []),
        ('PROM',     ['PROMENADE']),
        ('QDRT',     ['QUADRANT']),
        ('QYS',      ['QUAYS']),
        ('RMBL',     ['RAMBLE']),
        ('REST',     []),
        ('RTT',      ['RETREAT']),
        ('RDGE',     ['RIDGE']),
        ('RISE',     []),
        ('RD',       ['ROAD']),
        ('RTY',      ['ROTARY']),
        ('RTE',      ['ROUTE']),
        ('ROW',      []),
        ('RUE',      []),
        ('SVWY',     ['SERVICEWAY']),
        ('SHUN',     ['SHUNT']),
        ('SPUR',     []),
        ('SQ',       ['SQUARE']),
        ('ST',       ['STREET']),
        ('SBWY',     ['SUBWAY']),
        ('TARN',     []),
        ('TCE',      ['TERRACE']),
        ('THFR',     ['THOROUGHFARE']),
        ('TLWY',     ['TOLLWAY']),
        ('TOP',      []),
        ('TOR',      []),
        ('TRK',      ['TRACK']),
        ('TRL',      ['TRAIL']),
        ('TURN',     []),
        ('UPAS',     ['UNDERPASS']),
        ('VALE',     []),
        ('VIAD',     ['VIADUCT']),
        ('VIEW',     []),
        ('VSTA',     ['VISTA']),
        ('WALK',     []),
        ('WAY',      ['WY']),
        ('WKWY',     ['WALKWAY']),
        ('WHRF',     ['WHARF']),
        ('WYND',     [])
    ])

    thoroughfareSuffixAbbreviations = OrderedDict([
        ('CN',  ['CENTRAL']),
        ('E',   ['EAST']),
        ('EX',  ['EXTENSION']),
        ('LR',  ['LOWER']),
        ('N',   ['NORTH']),
        ('NE',  ['NORTH EAST']),
        ('NW',  ['NORTH WEST']),
        ('S',   ['SOUTH']),
        ('SE',  ['SOUTH EAST']),
        ('SW',  ['SOUTH WEST']),
        ('UP',  ['UPPER']),
        ('W',   ['WEST'])
    ])

    buildingTypeAbbreviations = OrderedDict([
        ('SHOPPING CENTRE', ["S/C", "SHOPNG CNTR", "SHOPPING CENTER", "SHOPPING CENTRE", "SHOPPING", "SHOP. CENTRE"]),
        ('PLAZA',           []),
        ('ARCADE',          []),
        ('MALL',            []),
        ('BUILDING',        ['BLDG']),
        ('FORUM',           [])
    ])

    deliveryTypeAbbreviations = OrderedDict([
        ('CARE PO',     []),
        ('GPO BOX',     []),
        ('LOCKED BAG',  []),
        ('PO BOX',      []),
        ('RMB',         [])
    ])

    countryAbbreviations = OrderedDict([
        ('AF', ['AFGHANISTAN']),
        ('AL', ['ALBANIA']),
        ('DZ', ['ALGERIA']),
        ('AS', ['AMERICAN SAMOA']),
        ('AD', ['ANDORRA']),
        ('AO', ['ANGOLA']),
        ('AI', ['ANGUILLA']),
        ('AQ', ['ANTARCTICA']),
        ('AG', ['ANTIGUA AND BARBUDA']),
        ('AR', ['ARGENTINA']),
        ('AM', ['ARMENIA']),
        ('AW', ['ARUBA']),
        ('AU', ['AUSTRALIA']),
        ('AT', ['AUSTRIA']),
        ('AZ', ['AZERBAIJAN']),
        ('BS', ['BAHAMAS']),
        ('BH', ['BAHRAIN']),
        ('BD', ['BANGLADESH']),
        ('BB', ['BARBADOS']),
        ('BY', ['BELARUS']),
        ('BE', ['BELGIUM']),
        ('BZ', ['BELIZE']),
        ('BJ', ['BENIN']),
        ('BM', ['BERMUDA']),
        ('BT', ['BHUTAN']),
        ('BO', ['BOLIVIA']),
        ('BQ', ['BONAIRE']),
        ('BA', ['BOSNIA AND HERZEGOVINA']),
        ('BW', ['BOTSWANA']),
        ('BV', ['BOUVET ISLAND']),
        ('BR', ['BRAZIL']),
        ('IO', ['BRITISH INDIAN OCEAN TERRITORY']),
        ('BN', ['BRUNEI DARUSSALAM']),
        ('BG', ['BULGARIA']),
        ('BF', ['BURKINA FASO']),
        ('BI', ['BURUNDI']),
        ('KH', ['CAMBODIA']),
        ('CM', ['CAMEROON']),
        ('CA', ['CANADA']),
        ('CV', ['CAPE VERDE']),
        ('KY', ['CAYMAN ISLANDS']),
        ('CF', ['CENTRAL AFRICAN REPUBLIC']),
        ('TD', ['CHAD']),
        ('CL', ['CHILE']),
        ('CN', ['CHINA']),
        ('CX', ['CHRISTMAS ISLAND']),
        ('CC', ['COCOS (KEELING) ISLANDS']),
        ('CO', ['COLOMBIA']),
        ('KM', ['COMOROS']),
        ('CG', ['CONGO']),
        ('CD', ['DEMOCRATIC REPUBLIC OF THE CONGO']),
        ('CK', ['COOK ISLANDS']),
        ('CR', ['COSTA RICA']),
        ('HR', ['CROATIA']),
        ('CU', ['CUBA']),
        ('CY', ['CYPRUS']),
        ('CZ', ['CZECH REPUBLIC']),
        ('DK', ['DENMARK']),
        ('DJ', ['DJIBOUTI']),
        ('DM', ['DOMINICA']),
        ('DO', ['DOMINICAN REPUBLIC']),
        ('EC', ['ECUADOR']),
        ('EG', ['EGYPT']),
        ('SV', ['EL SALVADOR']),
        ('GQ', ['EQUATORIAL GUINEA']),
        ('ER', ['ERITREA']),
        ('EE', ['ESTONIA']),
        ('ET', ['ETHIOPIA']),
        ('FK', ['FALKLAND ISLANDS (MALVINAS)']),
        ('FO', ['FAROE ISLANDS']),
        ('FJ', ['FIJI']),
        ('FI', ['FINLAND']),
        ('FR', ['FRANCE']),
        ('GF', ['FRENCH GUIANA']),
        ('PF', ['FRENCH POLYNESIA']),
        ('TF', ['FRENCH SOUTHERN TERRITORIES']),
        ('GA', ['GABON']),
        ('GM', ['GAMBIA']),
        ('GE', ['GEORGIA']),
        ('DE', ['GERMANY']),
        ('GH', ['GHANA']),
        ('GI', ['GIBRALTAR']),
        ('GR', ['GREECE']),
        ('GL', ['GREENLAND']),
        ('GD', ['GRENADA']),
        ('GP', ['GUADELOUPE']),
        ('GU', ['GUAM']),
        ('GT', ['GUATEMALA']),
        ('GG', ['GUERNSEY']),
        ('GN', ['GUINEA']),
        ('GW', ['GUINEA-BISSAU']),
        ('GY', ['GUYANA']),
        ('HT', ['HAITI']),
        ('HM', ['HEARD ISLAND AND MCDONALD MCDONALD ISLANDS']),
        ('VA', ['HOLY SEE (VATICAN CITY STATE)']),
        ('HN', ['HONDURAS']),
        ('HK', ['HONG KONG']),
        ('HU', ['HUNGARY']),
        ('IS', ['ICELAND']),
        ('IN', ['INDIA']),
        ('ID', ['INDONESIA']),
        ('IR', ['IRAN, ISLAMIC REPUBLIC OF']),
        ('IQ', ['IRAQ']),
        ('IE', ['IRELAND']),
        ('IM', ['ISLE OF MAN']),
        ('IL', ['ISRAEL']),
        ('IT', ['ITALY']),
        ('JM', ['JAMAICA']),
        ('JP', ['JAPAN']),
        ('JE', ['JERSEY']),
        ('JO', ['JORDAN']),
        ('KZ', ['KAZAKHSTAN']),
        ('KE', ['KENYA']),
        ('KI', ['KIRIBATI']),
        ('KP', ['KOREA, DEMOCRATIC PEOPLE\'S REPUBLIC OF']),
        ('KR', ['KOREA, REPUBLIC OF']),
        ('KW', ['KUWAIT']),
        ('KG', ['KYRGYZSTAN']),
        ('LA', ['LAO PEOPLE\'S DEMOCRATIC REPUBLIC']),
        ('LV', ['LATVIA']),
        ('LB', ['LEBANON']),
        ('LS', ['LESOTHO']),
        ('LR', ['LIBERIA']),
        ('LY', ['LIBYA']),
        ('LI', ['LIECHTENSTEIN']),
        ('LT', ['LITHUANIA']),
        ('LU', ['LUXEMBOURG']),
        ('MO', ['MACAO']),
        ('MK', ['MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF']),
        ('MG', ['MADAGASCAR']),
        ('MW', ['MALAWI']),
        ('MY', ['MALAYSIA']),
        ('MV', ['MALDIVES']),
        ('ML', ['MALI']),
        ('MT', ['MALTA']),
        ('MH', ['MARSHALL ISLANDS']),
        ('MQ', ['MARTINIQUE']),
        ('MR', ['MAURITANIA']),
        ('MU', ['MAURITIUS']),
        ('YT', ['MAYOTTE']),
        ('MX', ['MEXICO']),
        ('FM', ['MICRONESIA, FEDERATED STATES OF']),
        ('MD', ['MOLDOVA, REPUBLIC OF']),
        ('MC', ['MONACO']),
        ('MN', ['MONGOLIA']),
        ('ME', ['MONTENEGRO']),
        ('MS', ['MONTSERRAT']),
        ('MA', ['MOROCCO']),
        ('MZ', ['MOZAMBIQUE']),
        ('MM', ['MYANMAR']),
        ('NA', ['NAMIBIA']),
        ('NR', ['NAURU']),
        ('NP', ['NEPAL']),
        ('NL', ['NETHERLANDS']),
        ('NC', ['NEW CALEDONIA']),
        ('NZ', ['NEW ZEALAND']),
        ('NI', ['NICARAGUA']),
        ('NE', ['NIGER']),
        ('NG', ['NIGERIA']),
        ('NU', ['NIUE']),
        ('NF', ['NORFOLK ISLAND']),
        ('MP', ['NORTHERN MARIANA ISLANDS']),
        ('NO', ['NORWAY']),
        ('OM', ['OMAN']),
        ('PK', ['PAKISTAN']),
        ('PW', ['PALAU']),
        ('PS', ['PALESTINE, STATE OF']),
        ('PA', ['PANAMA']),
        ('PG', ['PAPUA NEW GUINEA']),
        ('PY', ['PARAGUAY']),
        ('PE', ['PERU']),
        ('PH', ['PHILIPPINES']),
        ('PN', ['PITCAIRN']),
        ('PL', ['POLAND']),
        ('PT', ['PORTUGAL']),
        ('PR', ['PUERTO RICO']),
        ('QA', ['QATAR']),
        ('RO', ['ROMANIA']),
        ('RU', ['RUSSIAN FEDERATION']),
        ('RW', ['RWANDA']),
        ('RE', ['REUNION']),
        ('BL', ['SAINT BARTHALEMY']),
        ('SH', ['SAINT HELENA']),
        ('KN', ['SAINT KITTS AND NEVIS']),
        ('LC', ['SAINT LUCIA']),
        ('MF', ['SAINT MARTIN (FRENCH PART)']),
        ('PM', ['SAINT PIERRE AND MIQUELON']),
        ('VC', ['SAINT VINCENT AND THE GRENADINES']),
        ('WS', ['SAMOA']),
        ('SM', ['SAN MARINO']),
        ('ST', ['SAO TOME AND PRINCIPE']),
        ('SA', ['SAUDI ARABIA']),
        ('SN', ['SENEGAL']),
        ('RS', ['SERBIA']),
        ('SC', ['SEYCHELLES']),
        ('SL', ['SIERRA LEONE']),
        ('SG', ['SINGAPORE']),
        ('SX', ['SINT MAARTEN (DUTCH PART)']),
        ('SK', ['SLOVAKIA']),
        ('SI', ['SLOVENIA']),
        ('SB', ['SOLOMON ISLANDS']),
        ('SO', ['SOMALIA']),
        ('ZA', ['SOUTH AFRICA']),
        ('GS', ['SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS']),
        ('SS', ['SOUTH SUDAN']),
        ('ES', ['SPAIN']),
        ('LK', ['SRI LANKA']),
        ('SD', ['SUDAN']),
        ('SR', ['SURINAME']),
        ('SJ', ['SVALBARD AND JAN MAYEN']),
        ('SZ', ['SWAZILAND']),
        ('SE', ['SWEDEN']),
        ('CH', ['SWITZERLAND']),
        ('SY', ['SYRIAN ARAB REPUBLIC']),
        ('TW', ['TAIWAN, PROVINCE OF CHINA']),
        ('TJ', ['TAJIKISTAN']),
        ('TZ', ['UNITED REPUBLIC OF TANZANIA']),
        ('TH', ['THAILAND']),
        ('TL', ['TIMOR-LESTE']),
        ('TG', ['TOGO']),
        ('TK', ['TOKELAU']),
        ('TO', ['TONGA']),
        ('TT', ['TRINIDAD AND TOBAGO']),
        ('TN', ['TUNISIA']),
        ('TR', ['TURKEY']),
        ('TM', ['TURKMENISTAN']),
        ('TC', ['TURKS AND CAICOS ISLANDS']),
        ('TV', ['TUVALU']),
        ('UG', ['UGANDA']),
        ('UA', ['UKRAINE']),
        ('AE', ['UNITED ARAB EMIRATES']),
        ('GB', ['UNITED KINGDOM']),
        ('US', ['UNITED STATES']),
        ('UM', ['UNITED STATES MINOR OUTLYING ISLANDS']),
        ('UY', ['URUGUAY']),
        ('UZ', ['UZBEKISTAN']),
        ('VU', ['VANUATU']),
        ('VE', ['VENEZUELA']),
        ('VN', ['VIET NAM']),
        ('VG', ['BRITISH VIRGIN ISLANDS']),
        ('VI', ['US VIRGIN ISLANDS']),
        ('WF', ['WALLIS AND FUTUNA']),
        ('EH', ['WESTERN SAHARA']),
        ('YE', ['YEMEN']),
        ('ZM', ['ZAMBIA']),
        ('ZW', ['ZIMBABWE']),
        ('AX', ['ALAND ISLANDS'])
    ])

    allowedPunctuation = ['\\-', '.', '\'']
    tokenDelimeters  = [r"\s", r"\d"] + list(set(SanitationUtils.punctuationChars) - set(allowedPunctuation))
    delimeterRegex   = r"[%s]" % "".join(tokenDelimeters)
    nondelimeterRegex= r"[^%s]" % "".join(tokenDelimeters)
    clearStartRegex  = r"(?<!%s)" % nondelimeterRegex
    clearFinishRegex = r"(?!%s)" % nondelimeterRegex
    numberRangeRegex = r"(\d+) ?- ?(\d+)"
    numberAlphaRegex = r"(\d+) ?([A-Z])"
    numberSlashRegex = r"(\d+)/(\d+)"
    alphaNumberRegex = r"[A-Z](\d+)"
    numberRegex      = r"(\d+)"
    nameRegex        = r"(%s+(\s*%s)*)" % (nondelimeterRegex, nondelimeterRegex)
    slashAbbrvRegex  = r"[A-Z]/[A-Z]+"
    multiNumberRegex = "|".join([
        numberAlphaRegex,
        numberRangeRegex,
        # numberSlashRegex,
        numberRegex
    ])
    
    floorLevelRegex = r"((?P<floor_prefix>FLOOR|LEVEL|LVL) )?(?P<floor_type>%s) ?(?P<floor_number>%s)" % (
        compileAbbrvRegex(floorAbbreviations),
        numberRegex,
    )
    subunitRegex = r"(?P<subunit_type>%s) ?(?P<subunit_number>%s)" % (
        compileAbbrvRegex(subunitAbbreviations),
        '|'.join([multiNumberRegex, alphaNumberRegex]),
    )
    stateRegex = r"(%s)" % compileAbbrvRegex(stateAbbreviations)
    thoroughfareTypeRegex = r"(?P<thoroughfare_type>%s)" % (
        compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    thoroughfareSuffixRegex = r"(?P<thoroughfare_suffix>%s)" % (
        compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    thoroughfareRegex = r"(?P<thoroughfare_number>%s)\s+(?P<thoroughfare_name>%s)\s+%s(?:\s+%s)?" % (
        multiNumberRegex,
        nameRegex,
        thoroughfareTypeRegex,
        thoroughfareSuffixRegex
    )
    buildingTypeRegex = r"(?P<building_type>%s)" % (
        compileAbbrvRegex(buildingTypeAbbreviations)
    )
    buildingRegex = r"(?P<building_name>%s)\s+%s" % (
        nameRegex,
        buildingTypeRegex
    )
    weakThoroughfareTypeRegex = r"(?P<weak_thoroughfare_type>%s)" % (
        compileAbbrvRegex(thoroughfareTypeAbbreviations)
    )
    weakThoroughfareSuffixRegex = r"(?P<weak_thoroughfare_suffix>%s)" % (
        compileAbbrvRegex(thoroughfareSuffixAbbreviations)
    )
    weakThoroughfareRegex = r"(?P<weak_thoroughfare_name>%s)\s+%s(?:\s+%s)?" % (
        nameRegex,
        weakThoroughfareTypeRegex,
        weakThoroughfareSuffixRegex
    )
    deliveryTypeRegex = r"(?P<delivery_type>%s)" % (
        compileAbbrvRegex(deliveryTypeAbbreviations),
    )
    deliveryRegex = r"%s(?:\s*(?P<delivery_number>%s))?" % (
        deliveryTypeRegex,
        "|".join([numberRegex, alphaNumberRegex])
    )
    countryRegex = r"(%s)" % compileAbbrvRegex(countryAbbreviations)

# [^,\s\d/()-]+
    addressTokenRegex = r"(%s)" % "|".join([
        clearStartRegex + deliveryRegex + clearFinishRegex,
        clearStartRegex + floorLevelRegex + clearFinishRegex,
        clearStartRegex + subunitRegex + clearFinishRegex,
        clearStartRegex + thoroughfareRegex + clearFinishRegex,
        clearStartRegex + buildingRegex + clearFinishRegex,
        # clearStartRegex + weakThoroughfareRegex + clearFinishRegex,
        clearStartRegex + stateRegex + clearFinishRegex,
        clearStartRegex + nameRegex + clearFinishRegex,
        clearStartRegex + numberRangeRegex + clearFinishRegex,
        # clearStartRegex + numberSlashRegex + clearFinishRegex,
        clearStartRegex + numberAlphaRegex + clearFinishRegex,
        clearStartRegex + numberRegex + clearFinishRegex,
        clearStartRegex + slashAbbrvRegex + clearFinishRegex

    ])

    @staticmethod
    def wrapClearRegex(regex):
        return AddressUtils.clearStartRegex + regex + AddressUtils.clearFinishRegex

    @staticmethod
    def identifyAbbreviation(abbrvDict, string):
        for abbrvKey, abbrvs in abbrvDict.items():
            if( string in [abbrvKey] + abbrvs):
                return abbrvKey
        return string

    @staticmethod
    def identifySubunit(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.subunitAbbreviations, string)

    @staticmethod
    def identifyFloor(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.floorAbbreviations, string)

    @staticmethod
    def identifyThoroughfareType(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.thoroughfareTypeAbbreviations, string)

    @staticmethod
    def identifyThoroughfareSuffix(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.thoroughfareSuffixAbbreviations, string)

    @staticmethod
    def identifyState(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.stateAbbreviations, string)

    @staticmethod
    def identifyBuildingType(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.buildingTypeAbbreviations, string)

    @staticmethod
    def identifyDeliveryType(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.deliveryTypeAbbreviations, string)

    @staticmethod
    def identifyCountry(string):
        return AddressUtils.identifyAbbreviation(AddressUtils.countryAbbreviations, string)

    @staticmethod
    def getSubunit(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.subunitRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('subunit_type') and matchDict.get('subunit_number')): 
            subunit_type = AddressUtils.identifySubunit(matchDict.get('subunit_type'))
            subunit_number = matchDict.get('subunit_number')
            if DEBUG_ADDRESS: print "FOUND SUBUNIT %s %s" % (subunit_type, subunit_number)
            return subunit_type, subunit_number
        return None

    @staticmethod
    def getFloor(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.floorLevelRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict): 
            floor_type = AddressUtils.identifyFloor(matchDict.get('floor_type'))
            floor_number = matchDict.get('floor_number')
            if DEBUG_ADDRESS: print "FOUND FLOOR %s %s" % (floor_type, floor_number)
            return floor_type, floor_number
        return None

    @staticmethod
    def getThoroughfare(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.thoroughfareRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('thoroughfare_name') and matchDict.get('thoroughfare_type')):
            thoroughfare_name = matchDict.get('thoroughfare_name')
            thoroughfare_type = AddressUtils.identifyThoroughfareType( 
                matchDict.get('thoroughfare_type') 
            )
            thoroughfare_suffix = AddressUtils.identifyThoroughfareSuffix(  
                matchDict.get('thoroughfare_suffix') 
            )
            thoroughfare_number = matchDict.get('thoroughfare_number')
            if DEBUG_ADDRESS: print "FOUND THOROUGHFARE (%s) %s | %s (%s)" % (
                thoroughfare_number,
                thoroughfare_name,
                thoroughfare_type,
                thoroughfare_suffix
            )
            return thoroughfare_number, thoroughfare_name, thoroughfare_type, thoroughfare_suffix
        return None

    @staticmethod
    def getBuilding(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.buildingRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict):
            building_name = matchDict.get('building_name')
            building_type = AddressUtils.identifyBuildingType(
                matchDict.get('building_type')
            )
            if DEBUG_ADDRESS: print "FOUND BUILDING %s %s" % (
                building_name, 
                building_type
            )
            return building_name, building_type

    @staticmethod
    def getWeakThoroughfare(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.weakThoroughfareRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('weak_thoroughfare_name') and matchDict.get('weak_thoroughfare_type')):
            # print matchDict
            weak_thoroughfare_name = matchDict.get('weak_thoroughfare_name')
            weak_thoroughfare_type = AddressUtils.identifyThoroughfareType( 
                matchDict.get('weak_thoroughfare_type')
            )
            weak_thoroughfare_suffix = AddressUtils.identifyThoroughfareSuffix(  
                matchDict.get('weak_thoroughfare_suffix')
            )

            if DEBUG_ADDRESS: print "FOUND WEAK THOROUGHFARE (%s) %s | %s (%s)" % (
                weak_thoroughfare_name,
                weak_thoroughfare_type,
                weak_thoroughfare_suffix
            )
            return weak_thoroughfare_name, weak_thoroughfare_type, weak_thoroughfare_suffix

    @staticmethod
    def getState(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.stateRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict and matchDict.get('state_name')):
            state_name = matchDict.get('state_name')
            if DEBUG_ADDRESS: print "FOUND SATE ", state_name
            return state_name

    @staticmethod
    def getDelivery(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.deliveryRegex
            ),
            token
        )
        matchDict = match.groupdict() if match else None
        if(matchDict):
            delivery_type = AddressUtils.identifyDeliveryType(matchDict.get('delivery_type'))
            delivery_number = matchDict.get('delivery_number')
            if DEBUG_ADDRESS: print "FOUND DELIVERY ", delivery_type, delivery_number
            return delivery_type, delivery_number

    @staticmethod
    def getName(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                AddressUtils.nameRegex
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            name = matchGrps[0]
            if DEBUG_ADDRESS: print "FOUND NAME ", repr(name)
            return name

    @staticmethod
    def getNumber(token):
        match = re.match(
            AddressUtils.wrapClearRegex(
                "(" + AddressUtils.multiNumberRegex + ")"
            ),
            token
        )
        matchGrps = match.groups() if match else None
        if(matchGrps):
            number = matchGrps[0]
            if DEBUG_ADDRESS: print "FOUND NUMBER ", repr(number)
            return number

    @staticmethod
    def sanitizeState(string):
        return SanitationUtils.compose(
            SanitationUtils.stripLeadingWhitespace,
            SanitationUtils.stripTailingWhitespace,
            SanitationUtils.stripExtraWhitespace,   
            SanitationUtils.stripPunctuation,
            SanitationUtils.toUpper
        )(string)

    @staticmethod
    def sanitizeAddressToken(string):
        string = SanitationUtils.stripExtraWhitespace(string)
        string = re.sub(AddressUtils.numberAlphaRegex + AddressUtils.clearStartRegex , r'\1\2', string)
        string = re.sub(AddressUtils.numberRangeRegex, r'\1-\2', string)
        if DEBUG: print "sanitizeAddressToken", SanitationUtils.coerceBytes( string)
        return string

    @staticmethod
    def tokenizeAddress(string):
        matches =  re.findall(
            AddressUtils.addressTokenRegex, 
            string.upper()
        )
        if DEBUG: print repr(matches)
        return map(
            lambda match: AddressUtils.sanitizeAddressToken(match[0]),
            matches    
        )

    @staticmethod
    def addressRemoveEndWord(string, word):
        string_layout = AddressUtils.tokenizeAddress(string)
        word_layout = AddressUtils.tokenizeAddress(word)
        if not(word_layout and string_layout): return string
        for i, word in enumerate(reversed(word_layout)):
            if( 1 + i > len(word_layout)) or word != string_layout[-1-i]:
                return string
        return " ".join(string_layout[:-len(word_layout)])

    @staticmethod
    def extractShop(address):
        match = re.match(AddressUtils.shopRegex, address)
        matchDict = match.groupdict()
        if(matchDict):
            number = matchDict.get('number', None) 
            rest = matchDict.get('rest', None)
            if(number):
                return number, rest
        return None, address

def testAddressUtils():
    pass
    # print AddressUtils.addressRemoveEndWord("WEST AUSTRALIA", "WEST AUSTRALIA")

    # print AddressUtils.addressRemoveEndWord("SHOP 7 KENWICK SHOPNG CNTR BELMONT RD, KENWICK WA (", "KENWICK WA")
    # print SanitationUtils.unicodeToByte(u"\u00FC ASD")
    # print "addressTokenRegex", AddressUtils.addressTokenRegex
    # print "thoroughfareRegex", AddressUtils.thoroughfareRegex
    # print "subunitRegex", AddressUtils.subunitRegex
    # print "floorLevelRegex", AddressUtils.floorLevelRegex
    # print "stateRegex", AddressUtils.stateRegex
    # print "delimeterRegex", AddressUtils.delimeterRegex

    # print AddressUtils.getSubunit("SHOP 4 A")
    # print AddressUtils.getFloor("LEVEL 8")

    # for line in [
    #     "8/5-7 KILVINGTON DRIVE EAST",
    #     "SH20 SANCTUARY LAKES SHOPPING CENTRE",
    #     "2 HIGH ST EAST BAYSWATER",
    #     "FLOREAT FORUM",
    #     "ANN LYONS",
    #     "SHOP 5, 370 VICTORIA AVE",
    #     "SHOP 34 ADELAIDE ARCADE",
    #     "SHOP 5/562 PENNANT HILLS RD",
    #     "MT OMMANEY SHOPPING",
    #     "BUCKLAND STREET",
    #     "6/7 118 RODWAY ARCADE",
    #     "INGLE FARM SHOPPING CENTRE",
    #     "EASTLAND SHOPPING CENTRE",
    #     "SHOP 3044 WESTFEILD",
    #     "303 HAWTHORN RD",
    #     "7 KALBARRI ST,  WA",
    #     "229 FORREST HILL CHASE",
    #     "THE VILLAGE SHOP 5",
    #     "GARDEN CITY SHOPPING CENTRE",
    #     "SHOP 2 EAST MALL",
    #     "SAMANTHA PALMER",
    #     "134 THE GLEN SHOPPING CENTRE",
    #     "SHOP 3 A, 24 TEDDER AVE",
    #     "SHOP 205, DANDENONG PLAZA",
    #     "SHOP 5 / 20 -21 OLD TOWN PLAZA",
    #     "18A BORONIA RD",
    #     "SHOP 426 LEVEL 4",
    #     "WATERFORD PLAZA",
    #     "BEAUDESERT RD",
    #     "173 GLENAYR AVE",
    #     "SHOP 14-16 ALBANY PLAZA S/C",
    #     "861 ALBANY HIGHWAY",
    #     "4/479 SYDNEY RD",
    #     "90 WINSTON AVE",
    #     "SHOP 2004 - LEVEL LG1",
    #     "142 THE PARADE",
    #     "46 MARKET STREET",
    #     "AUSTRALIA FAIR",
    #     "538 MAINS RD",
    #     "SHOP 28 GRENFELL ST",
    #     "309 MAIN ST",
    #     "60 TOMPSON ROAD",
    #     "SHOP 10 2-28 EVAN ST",
    #     "VENESSA MILETO",
    #     "BOX RD",
    #     "34 RAILWAY PARADE",
    #     "SHOP 14A WOODLAKE VILLAGE S/C",
    #     "17 ROKEBY RD",
    #     "AUSTRALIA FAIR SHOPPING",
    #     "SHOP 1, 18-26 ANDERSON ST",
    #     "INDOOROOPILLY SHOPPINGTOWN",
    #     "17 CASUARINA RD",
    #     "WHITFORDS WESTFIELD",
    #     "4, 175 LABOUCHERE RD",
    #     "2 PEEL STREET",
    #     "SHOP 71 THE ENTRANCE RD",
    #     "SHOP 2014 LEVEL 2",
    #     "PLAZA ARCADE",
    #     "SHOP 27 ADELAIDE ARCADE",
    #     "152 WENTWORTH RD",
    #     "92 PROSPECT RD",
    #     "31 REITA AVE",
    #     "33 NEW ENGLAND HWY",
    #     "46 HUNTER ST",
    #     "1/34-36 MCPHERSON ST",
    #     "SHOP 358",
    #     "147 SOUTH TCE",
    #     "SHOP 1003 L1",
    #     "357 CAMBRIDGE STREET",
    #     "495 BURWOOD HWY",
    #     "CAROUSAL MALL",
    #     "SHOP 22 BAYSIDE VILLAGE",
    #     "1/64 GYMEA BAY RD",
    #     "1/15 RAILWAY RD",
    #     "SOUTHLANDS BOULEVARD",
    #     "83A COMMERCIAL RD",
    #     u"456 ROCKY PT R\u010E",
    #     "95 ROCKEBY RD",
    #     "4/13-17 WARBURTON ST",
    #     "1/18 ADDISON SY",
    #     "SUNNYPARK",
    #     "SHOP 4,81 PROSPECT",
    #     "WESTFIELD",
    #     "15 - 16 KEVLAR CLOSE",
    #     "31",
    #     "3/71 DORE ST",
    #     "SHOP 11 RIVERSTONE PDE",
    #     "SOUTHERN RIVER SHOPPING CENTRE RANFORD ROAD",
    #     "6 RODINGA CLOSE",
    #     "SHOP 2013 WESTFIELDS",
    #     "SHOP 524 THE GLEN SHOPPING CENTRE",
    #     "JOONDALUP SHOPPING CENTRE",
    #     "48/14 JAMES PLACE",
    #     "3/66 TENTH AVE",
    #     "SHOP 23 GORDON VILLAGE ARCADE",
    #     "HORNSBY WESTFIELD",
    #     "SHOP 81",
    #     "215/152 BUNNERONG RD",
    #     "SP 1032 KNOX CITY SHOPPING CENTRE",
    #     "SHOP 152 RUNDLE MALL",
    #     "37 BURWOOD RD",
    #     "SHOP 52 LEVEL 3",
    #     "ALBANY PLAZA SHOPPING CENTRE",
    #     "LEVEL 3 SHOP 3094",
    #     "SHOP 19 B LAKE MACQUARIE",
    #     "18/70 HURTLE",
    #     "309 GEORGE ST",
    #     "76 EDWARDES",
    #     "SUNNYBANK PLAZA",
    #     "1/134 HIGH ST",
    #     "CARRUM DOWNS SHOPPING CENTER",
    #     "SHOP 13 1 WENTWORTH ST",
    #     "234 BROADWAY",
    #     "288 STATION ST",
    #     "KMART PLAZA",
    #     "15 FLINTLOCK CT",
    #     "17 O'CONNELL ST",
    #     "JILL STREET SHOPPING CENTRE",
    #     "SHOP 3, 2-10 WILLIAM THWAITES BLVD",
    #     "170 CLOVELLY RD",
    #     "SHOP 11 451 SYDNEY RD",
    #     "PRINCES HIGHWAY ULLADULLA",
    #     "WESTFIELD DONCASTER SHOPPING CENTRE",
    #     "153 BREBNER SR",
    #     "HELENSVALE TOWN CENTRE",
    #     "SHOP 7 A KENWICK SHOPNG CNTR 1 - 3 BELMONT RD EAST, KENWICK WA (",
    #     "3/3 HOWARD AVA",
    #     "8/2 RIDER BLVD",
    #     "ROBINA PARKWAY",
    #     "VICTORIA PT SHOPPING",
    #     "ROBINSON ROAD",
    #     "3/3 BEASLEY RD,",
    #     "39 HAWKESBURY RETREAT",
    #     "171 MORAYFIELD ROAD",
    #     "149 ST JOHN STREET",
    #     "49 GEORGE ST,  WA",
    #     "UNIT 1",
    #     "A8/90 MOUNT STREET",
    #     "114 / 23 CORUNNA RD",
    #     "43 GINGHAM STREET",
    #     "5 KERRY CRESCENT, WESTERN AUSTRALIA",
    #     "UNIT 2/33 MARTINDALE STREET",
    #     "207/67 WATT ST",
    #     "LEVEL 8, BLIGH"
    # ]:
    #     pass
        # print SanitationUtils.unicodeToByte("%64s %64s %s" % (line, AddressUtils.tokenizeAddress(line), AddressUtils.getThoroughfare(line)))


class TimeUtils:

    wpTimeFormat = "%Y-%m-%d %H:%M:%S"
    actTimeFormat = "%d/%m/%Y %I:%M:%S %p"
    gDriveTimeFormat = "%Y-%m-%d %H:%M:%S"

    @staticmethod
    def starStrptime(string, fmt = wpTimeFormat ):
        string = SanitationUtils.coerceUnicode(string)
        if(string):
            try:
                tstruct = time.strptime(string, fmt)
                if(tstruct):
                    return time.mktime(tstruct)
            except:
                pass
        return 0        

    @staticmethod
    def actStrptime(string):
        return TimeUtils.starStrptime(string, TimeUtils.actTimeFormat)

    # 2015-07-13 22:33:05
    @staticmethod
    def wpStrptime(string):
        return TimeUtils.starStrptime(string)

    @staticmethod
    def gDriveStrpTime(string):
        return TimeUtils.starStrptime(string, TimeUtils.gDriveTimeFormat)

    @staticmethod
    def wpTimeToString(t, fmt = wpTimeFormat):
        return time.strftime(fmt, time.localtime(t))

    @staticmethod
    def hasHappenedYet(t):
        assert isinstance(t, (int, float)), "param must be an int not %s"% type(t)
        return t >= time.time()

    @staticmethod
    def localToServerTime(t, timezoneOffset = time.timezone):
        return int(t - timezoneOffset)

    @staticmethod
    def serverToLocalTime(t, timezoneOffset = time.timezone):
        return int(t + timezoneOffset)

def testTimeUtils():
    gTime = TimeUtils.gDriveStrpTime("14/02/2016")
    print "gTime", gTime
    sTime = TimeUtils.localToServerTime(gTime)
    print "sTime", sTime

    print TimeUtils.wpTimeToString(1455379200)

    t1 = TimeUtils.actStrptime("29/08/2014 9:45:08 AM")
    t2 = TimeUtils.actStrptime("26/10/2015 11:08:31 AM")
    t3 = TimeUtils.wpStrptime("2015-07-13 22:33:05")
    t4 = TimeUtils.wpStrptime("2015-12-18 16:03:37")
    print [
        (t1, TimeUtils.wpTimeToString(t1)), 
        (t2, TimeUtils.wpTimeToString(t2)), 
        (t3, TimeUtils.wpTimeToString(t3)), 
        (t4, TimeUtils.wpTimeToString(t4))
    ]

class HtmlReporter(object):
    """docstring for htmlReporter"""

    class Section:
        def __init__(self, classname, title = None, description = "", data = "", length = None):
            if title is None: title = classname.title()
            self.title = title
            self.description = description
            self.data = data
            self.length = length
            self.classname = classname

        def toHtml(self):
            sectionID = SanitationUtils.makeSafeClass(self.classname)
            out  = '<div class="section">'
            out += '<a data-toggle="collapse" href="#{0}" aria-expanded="true" data-target="#{0}" aria-controls="{0}">'.format(sectionID)
            out += '<h2>' + self.title + (' ({})'.format(self.length) if self.length else '') + '</h2>'
            out += '</a>'
            out += '<div class="collapse" id="' + sectionID + '">'
            out += '<p class="description">' + (str(self.length) if self.length else "No") + ' ' + self.description + '</p>'
            out += '<p class="data">'
            out += SanitationUtils.sanitizeForXml(
                re.sub("<table>","<table class=\"table table-striped\">",self.data)
            )
            out += '</p>'
            out += '</div>'
            return out


    class Group:
        def __init__(self, classname, title = None, sections = None):
            if title is None: title = classname.title()
            if sections is None: sections = OrderedDict()
            self.title = title
            self.sections = sections
            self.classname = classname

        def addSection(self, section):
            self.sections[section.classname] = section

        def toHtml(self):
            out  = '<div class="group">'
            out += '<h1>' + self.title + '</h1>'
            for section in self.sections.values():
                out += section.toHtml()
            out += '</div>'
            return out

    groups = OrderedDict()

    def __init__(self):
        pass

    def addGroup( self, group):
        self.groups[group.classname] = group

    def getHead(self):
        return """\
<head>
    <meta charset="UTF-8">
    <!-- Latest compiled and minified CSS -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">

    <!-- Optional theme -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap-theme.min.css" integrity="sha384-fLW2N01lMqjakBkx3l/M9EahuwpSfeNvV63J5ezn3uZzapT0u7EYsXMjQV+0En5r" crossorigin="anonymous">
</head>
"""

    def getBody(self):
        return """
<body>
    {content}
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
</body>
""".format(
            content = "<br/>".join(
                group.toHtml() for group in self.groups.values()
            )
        )

    def getDocument(self):
        return """\
<!DOCTYPE html>
<html lang="en">
{head}
{body}
</html>
""".format(
            head=self.getHead(),
            body=self.getBody()
        )      

        
def testHTMLReporter():
    with\
             open('../output/htmlReporterTest.html', 'w+') as resFile,\
             io.open('../output/htmlReporterTestU.html', 'w+', encoding="utf8") as uresFile :
        reporter = HtmlReporter()

        matchingGroup = HtmlReporter.Group('matching', 'Matching Results')

        matchingGroup.addSection(
            HtmlReporter.Section(
                'perfect_matches', 
                **{
                    'title': 'Perfect Matches',
                    'description': "%s records match well with %s" % ("WP", "ACT"),
                    'data': u"<\U0001F44C'&>",
                    'length': 3
                }
            )
        )

        reporter.addGroup(matchingGroup)

        document = reporter.getDocument()
        print SanitationUtils.coerceBytes( document)
        uresFile.write( SanitationUtils.coerceUnicode(document))
        resFile.write( SanitationUtils.coerceAscii(document) )


class descriptorUtils:
    @staticmethod
    def safeKeyProperty(key):
        def getter(self):
            assert key in self.keys(), "{} must be set before get".format(key)
            return self[key]

        def setter(self, value):
            assert isinstance(value, (str, unicode)), "{} must be set with string not {}".format(key, type(value))
            self[key] = value

        return property(getter, setter)

class listUtils:
    @staticmethod
    def combineLists(a, b):
        if not a:
            return b if b else []
        if not b: return a
        return list(set(a) | set(b))

    @staticmethod
    def combineOrderedDicts(a, b):
        if not a:
            return b if b else OrderedDict()
        if not b: return a
        c = OrderedDict(a.items())
        for key, value in b.items():
            c[key] = value
        return c

    @staticmethod
    def filterUniqueTrue(a):
        b = []
        for i in a:
            if i and i not in b:
                b.append(i)
        return b

    @staticmethod
    def getAllkeys(*args):
        return listUtils.filterUniqueTrue(itertools.chain( *(
            arg.keys() for arg in args if isinstance(arg, dict)
        )))

    @staticmethod
    def keysNotIn(dictionary, keys):
        assert isinstance(dictionary, dict)
        return type(dictionary)([ \
            (key, value) for key, value in dictionary.items()\
            if key not in keys
        ])

class debugUtils:
    @staticmethod
    def getProcedure():
        return inspect.stack()[1][3]

    @staticmethod
    def getCallerProcedure():
        return inspect.stack()[2][3]   

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        try:
            bom = codecs.BOM_UTF8
            # print "bom: ", repr(bom)
            bomtest = f.read(len(bom))
            # print "bomtest: ", repr(bomtest)
            if(bomtest == bom):
                pass
                # print "starts with BOM_UTF8"
            else:
                raise Exception("does not start w/ BOM_UTF8")
        except Exception as e:
            if(e): pass
            # print "could not remove bom, ",e
            f.seek(0)
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        row = map(
            lambda x: "" if x is None else x,
            row
        )
        assert 'None' not in row
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        if data is None: data = ""
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class UnicodeDictWriter(UnicodeWriter):
    def __init__(self, f, fieldnames, dialect=csv.excel, encoding="utf-8", **kwds):
        UnicodeWriter.__init__(self, f, dialect, encoding, **kwds)
        self.fieldnames = fieldnames

    def writerow(self, rowDict):
        row = [SanitationUtils.coerceUnicode(rowDict.get(fieldname, "")) for fieldname in self.fieldnames]
        UnicodeWriter.writerow(self, row)

    def writeheader(self):
        UnicodeWriter.writerow(self, self.fieldnames)
    
def testUnicodeWriter():
    pass
    # testpath = "../output/UnicodeDictWriterTest.csv"
    # with open(testpath, 'w+') as testfile:
    #     writer = UnicodeDictWriter(testfile, ['a', 'b', 'c'])
    #     writer.writeheader()
    #     writer.writerow( {'a':1, 'b':2, 'c':u"\u00C3"})

    # with open(testpath, 'r') as testfile:
    #     for line in testfile.readlines():
    #         print line[:-1]
    
if __name__ == '__main__':
    # testHTMLReporter()
    # testTimeUtils()
    testSanitationUtils()
    # testUnicodeWriter()
    # testAddressUtils()