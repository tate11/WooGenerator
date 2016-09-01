"""
CSVParse_Gen_Tree
Introduces the "Generator" structure to the heirarchical CSV parser class CSVParse_Tree
and flat CSV parser class, CSVParse_Flat along with thier respective helper classses.
The Generator structure attaches metadata like code, name and description for all objects.
In heirarchical structures, the metadata for an object is generated by ananlysing its ancestors.
This allows a common metadata interface to be shared between heirarchical and nonheirarchical structures
"""

from collections import OrderedDict
from utils import descriptorUtils, SanitationUtils, listUtils
from csvparse_abstract import ObjList, ImportObject, CSVParse_Base
from csvparse_tree import CSVParse_Tree, ImportTreeItem, ImportTreeTaxo, ImportTreeObject
# from csvparse_shop import ImportShop, ProdList, CSVParse_Shop
from csvparse_flat import ImportFlat


# class GenProdList(ProdList):
#     def append(self, objectData):
#         assert issubclass(objectData.__class__, ImportGenProduct), \
#             "object must be subclass of ImportGenProduct not %s : %s" % (
#                 SanitationUtils.coerceUnicode(objectData.__class__),
#                 SanitationUtils.coerceUnicode(objectData)
#             )
#         return super(GenProdList, self).append(objectData)

# class GenItemList()
#
# class GenTaxoList(ObjList):
#     def append(self, objectData):
#         assert issubclass(objectData.__class__, ImportGenTaxo), \
#         "object must be subclass of ImportGenTaxo not %s : %s" % (
#         SanitationUtils.coerceUnicode(objectData.__class__),
#         SanitationUtils.coerceUnicode(objectData)
#         )
#         return super(GenTaxoList, self).append(objectData)

class ImportGenBase(ImportObject):
    "Provides basic Generator interface for Import classes as a mixin"
    codesumKey = 'codesum'
    descsumKey = 'descsum'
    namesumKey = 'itemsum'
    namesum     = descriptorUtils.safeKeyProperty(namesumKey)
    codesum     = descriptorUtils.safeKeyProperty(codesumKey)
    descsum     = descriptorUtils.safeKeyProperty(descsumKey)

    # def __init__(self, *args, **kwargs):
    #     if self.DEBUG_MRO:
    #         self.registerMessage(' ')
    #     super(ImportGenBase, self).__init__(*args, **kwargs)

    def verifyMeta(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        "Sanity checks that metadata has been processed correctly"
        # super(ImportGenBase, self).verifyMeta()
        keys = [
            self.namesumKey,
            self.codesumKey,
            self.descsumKey,
        ]
        for key in keys:
            assert key in self.keys(), key

    @property
    def index(self):
        return self.codesum

class ImportGenFlat(ImportFlat, ImportGenBase):
    "Base class for flat generator classes"
    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportGenFlat, self).__init__(*args, **kwargs)
        self.verifyMeta()


class ImportGenObject(ImportTreeObject, ImportGenBase):
    "Base class for heirarchical generator classes"

    codeKey = 'code'
    nameKey = 'name'
    fullnameKey = 'fullname'
    descriptionKey = 'HTML Description'
    fullnamesumKey = 'fullnamesum'

    code        = descriptorUtils.safeKeyProperty(codeKey)
    name        = descriptorUtils.safeKeyProperty(nameKey)
    fullname    = descriptorUtils.safeKeyProperty(fullnameKey)
    description = descriptorUtils.safeKeyProperty(descriptionKey)
    fullnamesum = descriptorUtils.safeKeyProperty(fullnamesumKey)

    nameDelimeter = ' '

    def __init__(self, *args, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        self.subs = kwargs.pop('subs', {})
        self.regex = kwargs.pop('regex', {})
        super(ImportGenObject, self).__init__(*args, **kwargs)

    @classmethod
    def fromImportTreeObject(cls, objectData, regex, subs):
        raise DeprecationWarning()
        # assert isinstance(objectData, ImportTreeObject)
        # row = objectData.row
        # rowcount = objectData.rowcount
        # depth = objectData.getDepth()
        # meta = objectData.getMeta()
        # parent = objectData.getParent()
        # return cls(objectData, rowcount, row, depth, meta, parent, regex, subs)

    def verifyMeta(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        super(ImportGenObject, self).verifyMeta()
        keys = [
            self.codeKey,
            self.nameKey,
            self.fullnameKey,
            self.fullnamesumKey
        ]
        for key in keys:
            assert key in self.keys()

    # @property
    # def index(self):
    #     return self.codesum

    @property
    def nameAncestors(self):
        return self.ancestors

    def getNameAncestors(self):
        raise DeprecationWarning("use .nameAncestors instead of .getNameAncestors()")
        return self.nameAncestors
        # return self.getAncestors()

    def getCodeDelimeter(self, other):
        return ''

    def joinCodes(self, ancestors):
        codeAncestors = [ancestor for ancestor in ancestors + [self] if ancestor.code ]
        if not codeAncestors:
            return ""
        prev = codeAncestors.pop(0)
        codesum = prev.code
        while codeAncestors:
            this = codeAncestors.pop(0)
            codesum += this.getCodeDelimeter(prev) + this.code
            prev = this
        return codesum

    def joinDescs(self, ancestors):
        if self.DEBUG_GEN:
            self.registerMessage(u"given description: {}".format( self.description) )
            self.registerMessage(u"self: {}".format( self.items()) )
        if self.description:
            return self.description
        fullnames = [self.fullname]
        for ancestor in reversed(ancestors):
            ancestorDescription = ancestor.description
            if ancestorDescription:
                return ancestorDescription
            ancestorFullname = ancestor.fullname
            if ancestorFullname:
                fullnames.insert(0, ancestorFullname)
        if fullnames:
            return " - ".join(reversed(fullnames))
        else:
            return ""

    # @property
    # def nameDelimeter(self):
    #     return ' '

    def getNameDelimeter(self):
        raise DeprecationWarning("use .nameDelimeter instead of .getNameDelimeter()")
        return ' '

    def joinNames(self, ancestors):
        ancestorsSelf = ancestors + [self]
        names = listUtils.filterUniqueTrue(map(lambda x: x.name, ancestorsSelf))
        nameDelimeter = self.nameDelimeter
        return nameDelimeter.join ( names )

    def joinFullnames(self, ancestors):
        ancestorsSelf = ancestors + [self]
        names = listUtils.filterUniqueTrue(map(lambda x: x.fullname, ancestorsSelf))
        nameDelimeter = self.nameDelimeter
        return nameDelimeter.join ( names )

    def changeName(self, name):
        return SanitationUtils.shorten(self.regex, self.subs, name)

    def processMeta(self):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        # super(ImportGenObject, self).processMeta()
        # meta = self.getMeta()
        meta = self.meta

        try:
            self.fullname =  meta[0]
        except KeyError:
            self.fullname =  ""
        # self.registerMessage("fullname: {}".format(self.fullname ) )

        try:
            self.code = meta[1]
        except KeyError:
            self.code = ""
        # self.registerMessage("code: {}".format(self.code ) )

        # ancestors = self.getAncestors()
        ancestors = self.ancestors

        codesum = self.joinCodes(ancestors)
        if self.DEBUG_GEN:
            self.registerMessage(u"codesum: {}".format( codesum) )
        self.codesum = codesum

        descsum = self.joinDescs(ancestors)
        if self.DEBUG_GEN:
            self.registerMessage(u"descsum: {}".format( descsum ) )
        self.descsum = descsum

        name = self.changeName(self.fullname)
        if self.DEBUG_GEN:
            self.registerMessage(u"name: {}".format( name ) )
        self.name = name

        # nameAncestors = self.getNameAncestors()
        nameAncestors = self.nameAncestors

        namesum = self.joinNames(nameAncestors)
        if self.DEBUG_GEN:
            self.registerMessage(u"namesum: {}".format( namesum) )
        self.namesum = namesum

        fullnamesum = self.joinFullnames(nameAncestors)
        if self.DEBUG_GEN:
            self.registerMessage(u"fullnamesum: {}".format( fullnamesum) )
        self.fullnamesum = fullnamesum


class ImportGenItem(ImportGenObject, ImportTreeItem):
    "Class for items in generator heirarchy"
    @property
    def nameAncestors(self):
        return self.itemAncestors

    def getNameAncestors(self):
        raise DeprecationWarning("use .nameAncestors instead of .getNameAncestors()")
        return self.nameAncestors
        # return self.getItemAncestors()

    def getCodeDelimeter(self, other):
        assert issubclass(type(other), ImportGenObject)
        if not other.isRoot and other.isTaxo:
            return '-'
        else:
            return super(ImportGenItem, self).getCodeDelimeter(other)

class ImportGenTaxo(ImportGenObject, ImportTreeTaxo):

    namesumKey = 'taxosum'
    namesum     = descriptorUtils.safeKeyProperty(namesumKey)

    nameDelimeter = ' > '

    def getNameDelimeter(self):
        raise DeprecationWarning("use .nameDelimeter instead of .getNameDelimeter()")
        return ' > '

class CSVParse_Gen_Mixin(CSVParse_Base):
    """
    Mixin class for parsers with generator interface
    """
    taxoContainer = ImportGenTaxo
    itemContainer = ImportGenItem
    # productContainer = ImportGenProduct
    containers = {}

    @classmethod
    def getCodeSum(cls, objectData):
        assert issubclass(type(objectData), ImportGenBase)
        return objectData.codesum

    @classmethod
    def getNameSum(cls, objectData):
        assert issubclass(type(objectData), ImportGenBase)
        return objectData.namesum

    def sanitizeCell(self, cell):
        return SanitationUtils.sanitizeCell(cell)

class CSVParse_Gen_Tree(CSVParse_Tree, CSVParse_Gen_Mixin): #, CSVParse_Shop):
    """ Parser for tree-based generator structure """

    def __init__(self, cols, defaults, schema, \
                    taxoSubs={}, itemSubs={}, taxoDepth=2, itemDepth=2, metaWidth=2):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        assert metaWidth >= 2, "metaWidth must be greater than 2 for a GEN subclass"
        extra_defaults = OrderedDict([
            ('CVC', '0'),
            ('code', ''),
            ('name', ''),
            ('fullname', ''),
            ('description', ''),
            ('HTML Description', ''),
            ('imglist', [])
        ])
        extra_taxoSubs = OrderedDict([
            ('', ''),
        ])
        extra_itemSubs = OrderedDict([
            ('Hot Pink', 'Pink'),
            ('Hot Lips (Red)', 'Red'),
            ('Hot Lips', 'Red'),
            ('Silken Chocolate (Bronze)', 'Bronze'),
            ('Silken Chocolate', 'Bronze'),
            ('Moon Marvel (Silver)', 'Silver'),
            ('Dusty Gold', 'Gold'),

            ('Screen Printed', ''),
            ('Embroidered', ''),
        ])
        extra_cols = [schema]

        cols = listUtils.combineLists( cols, extra_cols )
        defaults = listUtils.combineOrderedDicts( defaults, extra_defaults )
        super(CSVParse_Gen_Tree, self).__init__( cols, defaults, taxoDepth, itemDepth, metaWidth)
        # CSVParse_Gen_Mixin.__init__(self, schema)

        self.schema     = schema
        self.taxoSubs   = listUtils.combineOrderedDicts( taxoSubs, extra_taxoSubs )
        self.itemSubs   = listUtils.combineOrderedDicts( itemSubs, extra_itemSubs )
        self.taxoRegex  = SanitationUtils.compileRegex(self.taxoSubs)
        self.itemRegex  = SanitationUtils.compileRegex(self.itemSubs)

        if self.DEBUG_GEN:
            self.registerMessage("taxoDepth: {}".format(self.taxoDepth), 'CSVParse_Gen_Tree.__init__')
            self.registerMessage("itemDepth: {}".format(self.itemDepth), 'CSVParse_Gen_Tree.__init__')
            self.registerMessage("maxDepth: {}".format(self.maxDepth), 'CSVParse_Gen_Tree.__init__')
            self.registerMessage("metaWidth: {}".format(self.metaWidth), 'CSVParse_Gen_Tree.__init__')
            self.registerMessage("schema: {}".format(self.schema), 'CSVParse_Gen_Tree.__init__')

    def getNewObjContainer(self, allData, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        container = super(CSVParse_Gen_Tree, self).getNewObjContainer( allData, **kwargs)
        if issubclass( container, ImportTreeItem ):
            if self.DEBUG_GEN:
                self.registerMessage("super resulted in item container")
            itemtype = allData.get(self.schema,'')
            if self.DEBUG_GEN:
                self.registerMessage("itemtype: {}".format(itemtype))
            if itemtype in self.containers.keys():
                container = self.containers[itemtype]
        else:
            if self.DEBUG_GEN:
                self.registerMessage("super resulted in non-item container")
        return container


    # def clearTransients(self):
    #     super(CSVParse_Gen_Tree, self).clearTransients()
        # CSVParse_Shop.clearTransients(self)

    # def registerItem(self, itemData):
    #     super(CSVParse_Gen_Tree, self).registerItem(itemData)
    #     if itemData.isProduct:
    #         self.registerProduct(itemData)

    def changeItem(self, item):
        return SanitationUtils.shorten(self.itemRegex, self.itemSubs, item)

    def changeFullname(self, item):
        subs = OrderedDict([(' \xe2\x80\x94 ', ' ')])
        return SanitationUtils.shorten(SanitationUtils.compileRegex(subs), subs, item)

    def depth(self, row):
        for i, cell in enumerate(row):
            if cell:
                return i
            if i >= self.maxDepth:
                return -1
        return -1

    def getKwargs(self, allData, container, **kwargs):
        if self.DEBUG_MRO:
            self.registerMessage(' ')
        kwargs = super(CSVParse_Gen_Tree, self).getKwargs(allData, container, **kwargs)
        assert issubclass(container, ImportGenObject)
        if issubclass(container, self.taxoContainer):
            regex = self.taxoRegex
            subs = self.taxoSubs
        else:
            assert issubclass(container, self.itemContainer), "class must be item or taxo subclass not %s" % container.__name__
            regex = self.itemRegex
            subs = self.itemSubs
        kwargs['regex'] = regex
        kwargs['subs'] = subs
        for key in ['regex', 'subs']:
            assert kwargs[key] is not None
        return kwargs

    # def newObject(self, rowcount, row, **kwargs):
    #     return super(CSVParse_Gen_Tree, self).newObject(rowcount, row, **kwargs)
