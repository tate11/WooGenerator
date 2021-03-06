# -*- coding: utf-8 -*-
from __future__ import absolute_import

from collections import OrderedDict

from .core import SyncClientWC, SyncClientWCLegacy
from .xero import SyncClientXero
from ..coldata import ColDataProductMeridian, ColDataWcProdCategory

class ProdSyncClientMixin(object):
    endpoint_singular = 'product'
    coldata_class = ColDataProductMeridian

class ProdSyncClientWC(SyncClientWC, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular
    coldata_class = ProdSyncClientMixin.coldata_class

class ProdSyncClientWCLegacy(SyncClientWCLegacy, ProdSyncClientMixin):
    endpoint_singular = ProdSyncClientMixin.endpoint_singular
    coldata_class = ProdSyncClientMixin.coldata_class

class CatSyncClientMixin(object):
    endpoint_singular = 'product_category'
    endpoint_plural = 'products/categories'
    coldata_class = ColDataWcProdCategory
    primary_key_handle = 'term_id'

    def analyse_remote_categories(self, parser, **kwargs):
        taxo_api_iterator = self.get_iterator(self.endpoint_plural)
        categories = []
        for page in taxo_api_iterator:
            if self.page_nesting:
                page = page['product_categories']
            for page_item in page:
                categories.append(page_item)
        parser.process_api_categories_raw(categories)
        if self.DEBUG_API:
            self.register_message("Analysed categories:")
            self.register_message(parser.to_str_tree())

class CatSyncClientWC(SyncClientWC, CatSyncClientMixin):
    endpoint_singular = CatSyncClientMixin.endpoint_singular
    endpoint_plural = CatSyncClientMixin.endpoint_plural
    coldata_class = CatSyncClientMixin.coldata_class
    primary_key_handle = CatSyncClientMixin.primary_key_handle

class CatSyncClientWCLegacy(SyncClientWCLegacy):
    endpoint_singular = CatSyncClientMixin.endpoint_singular
    endpoint_plural = CatSyncClientMixin.endpoint_plural
    coldata_class = CatSyncClientMixin.coldata_class
    primary_key_handle = CatSyncClientMixin.primary_key_handle

class ProdSyncClientXero(SyncClientXero):
    endpoint_singular = 'item'
