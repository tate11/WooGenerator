"""Module for generating woocommerce csv import files from Google Drive Data."""

from __future__ import absolute_import

import io
import os
import shutil
import sys
import time
import traceback
import webbrowser
import zipfile
from bisect import insort
from collections import OrderedDict
from pprint import pformat, pprint

from exitstatus import ExitStatus
from requests.exceptions import ConnectionError, ConnectTimeout, ReadTimeout

from .images import process_images
from .matching import (AttacheeSkuMatcher, CategoryMatcher, ImageMatcher,
                       ProductMatcher, VariationMatcher)
from .namespace.core import (MatchNamespace, ParserNamespace, ResultsNamespace,
                             UpdateNamespace)
from .namespace.prod import SettingsNamespaceProd
from .parsing.api import ApiParseWoo
from .parsing.dyn import CsvParseDyn
from .parsing.special import CsvParseSpecial
from .parsing.woo import WooCatList
from .utils import (ProgressCounter, Registrar, SanitationUtils, SeqUtils,
                    TimeUtils)
from .utils.reporter import (ReporterNamespace, do_cat_sync_gruop,
                             do_category_matches_group, do_delta_group,
                             do_duplicates_group, do_duplicates_summary_group,
                             do_failures_group, do_main_summary_group,
                             do_matches_group, do_matches_summary_group,
                             do_post_summary_group, do_successes_group,
                             do_sync_group, do_variation_matches_group,
                             do_variation_sync_group)


def timediff(settings):
    """Return time elapsed since start."""
    return time.time() - settings.start_time


def check_warnings(settings):
    """
    Check if there have been any errors or warnings registered in Registrar.

    Raise approprriate exceptions if needed
    """
    if Registrar.errors:
        print("there were some urgent errors "
              "that need to be reviewed before continuing")
        Registrar.print_message_dict(0)
        status = ExitStatus.failure
        print "\nexiting with status %s\n" % status
        sys.exit(status)
    elif Registrar.warnings:
        print "there were some warnings that should be reviewed"
        Registrar.print_message_dict(1)


def populate_master_parsers(parsers, settings):
    """Create and populates the various parsers."""
    Registrar.register_message('schema: %s, woo_schemas: %s' % (
        settings.schema, settings.woo_schemas
    ))

    parsers.dyn = CsvParseDyn()
    parsers.special = CsvParseSpecial()

    if Registrar.DEBUG_GEN:
        Registrar.register_message(
            "master_download_client_args: %s" %
            settings.master_download_client_args)

    with settings.master_download_client_class(**settings.master_download_client_args) as client:

        if settings.schema_is_woo:
            if settings.do_dyns:
                Registrar.register_message("analysing dprc rules")
                client.analyse_remote(
                    parsers.dyn,
                    data_path=settings.dprc_path,
                    gid=settings.dprc_gid
                )
                settings.dprc_rules = parsers.dyn.taxos

                Registrar.register_message("analysing dprp rules")
                parsers.dyn.clear_transients()
                client.analyse_remote(
                    parsers.dyn,
                    data_path=settings.dprp_path,
                    gid=settings.dprp_gid
                )
                settings.dprp_rules = parsers.dyn.taxos

            if settings.do_specials:
                Registrar.register_message("analysing specials")
                client.analyse_remote(
                    parsers.special,
                    data_path=settings.specials_path,
                    gid=settings.spec_gid
                )
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message(
                        "all specials: %s" % parsers.special.tabulate()
                    )

                settings.special_rules = parsers.special.rules

                settings.current_special_groups = parsers.special.determine_current_spec_grps(
                    specials_mode=settings.specials_mode,
                    current_special=settings.current_special
                )
                if Registrar.DEBUG_SPECIAL:
                    Registrar.register_message(
                        "current_special_groups: %s" % settings.current_special_groups
                    )

        master_parser_args = settings.master_parser_args

        if os.path.exists(settings.master_path):
            master_mod_ts = max(
                os.path.getmtime(settings.master_path), os.path.getctime(settings.master_path)
            )
            master_mod_dt = TimeUtils.timestamp2datetime(master_mod_ts)
            master_parser_args['defaults'].update({
                'Updated': master_mod_dt,
                'modified_gmt': TimeUtils.datetime_local2gmt(master_mod_dt)
            })


        parsers.master = settings.master_parser_class(
            **master_parser_args
        )

        Registrar.register_progress("analysing master product data")

        analysis_kwargs = {
            'data_path': settings.master_path,
            'gid': settings.gen_gid,
            'limit': settings['master_parse_limit']
        }
        if Registrar.DEBUG_PARSER:
            Registrar.register_message("analysis_kwargs: %s" % analysis_kwargs)

        client.analyse_remote(parsers.master, **analysis_kwargs)

        if Registrar.DEBUG_PARSER and hasattr(
                parsers.master, 'categories_name'):
            for category_name, category_list in getattr(
                    parsers.master, 'categories_name').items():
                if len(category_list) < 2:
                    continue
                if SeqUtils.check_equal(
                        [category.namesum for category in category_list]):
                    continue
                Registrar.register_warning("bad category: %50s | %d | %s" % (
                    category_name[:50], len(category_list), str(category_list)
                ))

        return parsers


def populate_slave_parsers(parsers, settings):
    """Populate the parsers for data from the slave database."""

    parsers.slave = settings.slave_parser_class(**settings.slave_parser_args)

    slave_client_class = settings.slave_download_client_class
    slave_client_args = settings.slave_download_client_args

    # with ProdSyncClientWC(settings['slave_wp_api_params']) as client:

    if settings.schema_is_woo and settings['do_images']:
        Registrar.register_progress("analysing API image data")
        img_client_class = settings.slave_img_sync_client_class
        img_client_args = settings.slave_img_sync_client_args

        with img_client_class(**img_client_args) as client:
            client.analyse_remote_imgs(
                parsers.slave,
                data_path=settings.slave_img_path
            )

    if settings.schema_is_woo and settings['do_categories']:
        Registrar.register_progress("analysing API category data")

        cat_sync_client_class = settings.slave_cat_sync_client_class
        cat_sync_client_args = settings.slave_cat_sync_client_args

        with cat_sync_client_class(**cat_sync_client_args) as client:
            client.analyse_remote_categories(
                parsers.slave,
                data_path=settings.slave_cat_path
            )


    with slave_client_class(**slave_client_args) as client:
        # try:

        Registrar.register_progress("analysing API data")

        # Registrar.DEBUG_ABSTRACT = True
        # Registrar.DEBUG_API = True
        # Registrar.DEBUG_GEN = True
        # Registrar.DEBUG_TREE = True
        # Registrar.DEBUG_WOO = True
        # Registrar.DEBUG_TRACE = True
        # ApiParseWoo.product_resolver = Registrar.exception_resolver
        client.analyse_remote(
            parsers.slave,
            data_path=settings.slave_path
        )

    if Registrar.DEBUG_CLIENT:
        container = settings.slave_parser_class.product_container.container
        prod_list = container(parsers.slave.products.values())
        Registrar.register_message("Products: \n%s" % prod_list.tabulate())

    return parsers

def export_master_parser(settings, parsers):
    """Export key information from master parser to csv."""
    Registrar.register_progress("Exporting Master info to disk")

    product_colnames = settings.coldata_class.get_col_values_native('path', target='wc-csv')

    for col in settings['exclude_cols']:
        if col in product_colnames:
            del product_colnames[col]

    if settings.schema_is_woo:
        attribute_colnames = settings.coldata_class.get_attribute_colnames_native(
            parsers.master.attributes, parsers.master.vattributes)
        product_colnames = SeqUtils.combine_ordered_dicts(
            product_colnames, attribute_colnames
        )

    container = parsers.master.product_container.container

    product_list = container(parsers.master.products.values())
    product_list.export_items(settings.fla_path, product_colnames)

    if settings.schema_is_woo:
        # variations
        variation_container = settings.master_parser_class.variation_container.container
        # variation_cols = settings.coldata_class_var.get_col_data_native('write', target='wc-csv')
        variation_col_names = settings.coldata_class_var.get_col_values_native('path', target='wc-csv')
        attribute_meta_col_names = settings.coldata_class_var.get_attribute_meta_colnames_native(
            parsers.master.vattributes)
        variation_col_names = SeqUtils.combine_ordered_dicts(
            variation_col_names, attribute_meta_col_names
        )
        if settings.do_variations and parsers.master.variations:

            variation_list = variation_container(parsers.master.variations.values())
            variation_list.export_items(settings.flv_path, variation_col_names)

            updated_variations = parsers.master.updated_variations.values()

            if updated_variations:
                updated_variations_list = variation_container(updated_variations)
                updated_variations_list.export_items(
                    settings.flvu_path, variation_col_names
                )

        # categories
        if settings.do_categories and parsers.master.categories:
            # category_cols = settings.coldata_class_cat.get_col_data_native('write', target='wc-csv')
            category_col_names = settings.coldata_class_cat.get_col_values_native('path', target='wc-csv')
            category_container = settings.master_parser_class.category_container.container
            category_list = category_container([
                category for category in parsers.master.categories.values()
                if category.members
            ])
            category_list.export_items(settings.cat_path, category_col_names)

        # specials
        if settings.do_specials and settings.current_special_id:
            special_products = parsers.master.onspecial_products.values()
            if special_products:
                special_product_list = container(special_products)
                special_product_list.export_items(
                    settings.fls_path, product_colnames
                )
            special_variations = parsers.master.onspecial_variations.values()
            if special_variations:
                sp_variation_list = variation_container(special_variations)
                sp_variation_list.export_items(
                    settings.flvs_path, variation_col_names
                )

        updated_products = parsers.master.updated_products.values()
        if updated_products:
            updated_product_list = container(updated_products)
            updated_product_list.export_items(
                settings.flu_path, product_colnames
            )

    Registrar.register_progress("CSV Files have been created.")

def cache_api_data(settings, parsers):
    """Export key information from slave parser to csv."""
    if not settings.download_slave:
        return

    Registrar.register_progress("Exporting Slave info to disk")
    container = settings.slave_parser_class.product_container.container
    product_list = container(parsers.slave.products.values())
    product_list.export_api_data(settings.slave_path)

    if settings.do_categories and parsers.slave.categories:
        category_container = settings.slave_parser_class.category_container.container
        category_list = category_container(parsers.slave.categories.values())
        category_list.export_api_data(settings.slave_cat_path)

    if settings.do_images and parsers.slave.attachments:
        attachment_container = settings.slave_parser_class.attachment_container.container
        image_list = attachment_container(parsers.slave.attachments.values())
        image_list.export_api_data(settings.slave_img_path)

def do_match_images(parsers, matches, settings):
    if Registrar.DEBUG_IMG:
        Registrar.register_message(
            "matching %d master attachments with %d slave attachments" %
            (len(parsers.master.attachments),
             len(parsers.slave.attachments)))

    matches.image = MatchNamespace(
        index_fn=ImageMatcher.image_index_fn
    )

    image_matcher = ImageMatcher()
    image_matcher.clear()
    slave_imgs_attachments = OrderedDict([
        (index, image) for index, image in parsers.slave.attachments.items()
        if image.attaches.has_products_categories
    ])
    master_imgs_attachments = OrderedDict([
        (index, image) for index, image in parsers.master.attachments.items()
        if image.attaches.has_products_categories
    ])
    image_matcher.process_registers(
        slave_imgs_attachments, master_imgs_attachments
    )

    matches.image.globals.add_matches(image_matcher.pure_matches)
    matches.image.masterless.add_matches(image_matcher.masterless_matches)
    matches.image.slaveless.add_matches(image_matcher.slaveless_matches)

    if Registrar.DEBUG_IMG:
        if image_matcher.pure_matches:
            Registrar.register_message("All Image matches:\n%s" % (
                '\n'.join(map(str, image_matcher.matches))))

    matches.image.valid += image_matcher.pure_matches

    if image_matcher.duplicate_matches:
        matches.image.duplicate['file_name'] = image_matcher.duplicate_matches
        if Registrar.DEBUG_IMG:
            Registrar.register_message(
                'filename matcher duplicates:\n%s' % (
                    image_matcher.duplicate_matches
                )
            )
        # for match in image_matcher.duplicate_matches:
        #     master_filenames = [img.file_name for img in match.m_objects]
        #     if all(master_filenames) \
        #     and SeqUtils.check_equal(master_filenames):
        #         matches.image.valid.append(match)
        #     else:
        #         matches.image.invalid.append(match)
        #         continue
        # if matches.image.invalid:
        #     exc = UserWarning(
        #         "attachments couldn't be synchronized because of ambiguous filenames:\n%s"
        #         % '\n'.join(map(str, matches.image.invalid)))
        #     Registrar.register_error(exc)
        #     raise exc

    attachee_sku_matcher = AttacheeSkuMatcher(
        matches.image.globals.s_indices, matches.image.globals.m_indices
    )
    attachee_sku_matcher.process_registers(
        slave_imgs_attachments, master_imgs_attachments
    )

    # make sure that all duplicates are resolved after matching using attachee_sku
    if Registrar.DEBUG_IMG:
        Registrar.register_message(
            "adding attache_sku_matcher.pure_matches:\n%s" % (
                attachee_sku_matcher.pure_matches.tabulate()
            )
        )
    matches.image.valid += attachee_sku_matcher.pure_matches
    filename_duplicate_indices_m = set([
        attachment.index \
        for match in image_matcher.duplicate_matches
        for attachment in match.m_objects
    ])
    attachee_sku_pure_indices_m = set([
        attachment.index \
        for match in attachee_sku_matcher.pure_matches
        for attachment in match.m_objects
    ])
    assert \
    attachee_sku_pure_indices_m.issuperset(filename_duplicate_indices_m), \
    (
        "all master indices from filename duplicates should be contained in "
        "attache_sku pure match indices:\nfilename:\n%s\nattachee_sku:\n%s"
    ) % (
        filename_duplicate_indices_m,
        attachee_sku_pure_indices_m
    )
    filename_duplicate_indices_s = set([
        attachment.index \
        for match in image_matcher.duplicate_matches
        for attachment in match.s_objects
    ])
    attachee_sku_pure_indices_s = set([
        attachment.index \
        for match in attachee_sku_matcher.pure_matches
        for attachment in match.s_objects
    ])
    assert \
    attachee_sku_pure_indices_s.issuperset(filename_duplicate_indices_s), \
    (
        "all slave indices from filename duplicates should be contained in "
        "attache_sku pure match indices:\nfilename:\n%s\nattachee_sku:\n%s"
    ) % (
        filename_duplicate_indices_s,
        attachee_sku_pure_indices_s
    )


    return matches

def do_match_categories(parsers, matches, settings):
    if Registrar.DEBUG_CATS:
        Registrar.register_message(
            "matching %d master categories with %d slave categories" %
            (len(parsers.master.categories),
             len(parsers.slave.categories)))

    if not( parsers.master.categories and parsers.slave.categories ):
        return matches

    matches.category = MatchNamespace(
        index_fn=CategoryMatcher.category_index_fn
    )

    category_matcher = CategoryMatcher()
    category_matcher.clear()
    category_matcher.process_registers(
        parsers.slave.categories, parsers.master.categories
    )

    matches.category.globals.add_matches(category_matcher.pure_matches)
    matches.category.masterless.add_matches(
        category_matcher.masterless_matches)
    # matches.deny_anomalous(
    #     'category_matcher.masterless_matches', category_matcher.masterless_matches
    # )
    matches.category.slaveless.add_matches(category_matcher.slaveless_matches)
    # matches.deny_anomalous(
    #     'category_matcher.slaveless_matches', category_matcher.slaveless_matches
    # )

    if Registrar.DEBUG_CATS:
        if category_matcher.pure_matches:
            Registrar.register_message("All Category matches:\n%s" % (
                '\n'.join(map(str, category_matcher.matches))))

    matches.category.valid += category_matcher.pure_matches

    if category_matcher.duplicate_matches:
        matches.category.duplicate['title'] = category_matcher.duplicate_matches

        for match in category_matcher.duplicate_matches:
            master_taxo_sums = [cat.namesum for cat in match.m_objects]
            if all(master_taxo_sums) \
                    and SeqUtils.check_equal(master_taxo_sums) \
                    and not len(match.s_objects) > 1:
                matches.category.valid.append(match)
            else:
                matches.category.invalid.append(match)
        if matches.category.invalid:
            exc = UserWarning(
                "categories couldn't be synchronized because of ambiguous names:\n%s"
                % '\n'.join(map(str, matches.category.invalid)))
            Registrar.register_error(exc)
            raise exc

    if category_matcher.slaveless_matches and category_matcher.masterless_matches:
        exc = UserWarning(
            "You may want to fix up the following categories before syncing:\n%s\n%s"
            %
            ('\n'.join(map(str, category_matcher.slaveless_matches)),
             '\n'.join(map(str, category_matcher.masterless_matches))))
        Registrar.register_error(exc)
        # raise exc

    # print parsers.master.to_str_tree()
    # if Registrar.DEBUG_CATS:
    #     print "product parser"
    #     for key, category in parsers.master.categories.items():
    #         print "%5s | %50s | %s" % (key, category.title[:50],
    #                                    category.wpid)
    # if Registrar.DEBUG_CATS:
    #     print "api product parser info"
    #     print "there are %s slave categories registered" % len(
    #         parsers.slave.categories)
    #     print "there are %s children of API root" % len(
    #         parsers.slave.root_data.children)
    #     print parsers.slave.to_str_tree()
    #     for key, category in parsers.slave.categories.items():
    #         print "%5s | %50s" % (key, category.title[:50])

    return matches


def do_match_prod(parsers, matches, settings):
    """For every item in slave, find its counterpart in master."""

    Registrar.register_progress("Attempting matching")

    matches.variation = MatchNamespace(
        index_fn=ProductMatcher.product_index_fn
    )

    if settings['do_categories']:
        matches.category.prod = OrderedDict()

    if not settings.do_sync:
        return matches

    product_matcher = ProductMatcher()
    product_matcher.process_registers(
        parsers.slave.products, parsers.master.products
    )
    # print product_matcher.__repr__()

    matches.globals.add_matches(product_matcher.pure_matches)
    matches.masterless.add_matches(product_matcher.masterless_matches)
    matches.deny_anomalous(
        'product_matcher.masterless_matches', product_matcher.masterless_matches
    )
    matches.slaveless.add_matches(product_matcher.slaveless_matches)
    matches.deny_anomalous(
        'product_matcher.slaveless_matches', product_matcher.slaveless_matches
    )

    try:
        matches.deny_anomalous(
            'product_matcher.duplicate_matches',
            product_matcher.duplicate_matches,
            True
        )
    except AssertionError as exc:
        exc = UserWarning(
            "products couldn't be synchronized because of ambiguous SKUs:%s"
            % '\n'.join(map(str, product_matcher.duplicate_matches)))
        Registrar.register_error(exc)
        raise exc

    if settings['do_categories']:

        category_matcher = CategoryMatcher()

        for _, prod_match in enumerate(matches.globals):
            if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
                Registrar.register_message("processing prod_match: %s" %
                                           prod_match.tabulate())
            m_object = prod_match.m_object
            s_object = prod_match.s_object
            match_index = prod_match.singular_index

            category_matcher.clear()
            category_matcher.process_registers(
                s_object.categories, m_object.categories
            )

            matches.category.prod[match_index] = MatchNamespace(
                index_fn=CategoryMatcher.category_index_fn)

            matches.category.prod[match_index].globals.add_matches(
                category_matcher.pure_matches
            )
            matches.category.prod[match_index].masterless.add_matches(
                category_matcher.masterless_matches
            )
            matches.category.prod[match_index].slaveless.add_matches(
                category_matcher.slaveless_matches
            )

            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "category matches for update:\n%s" % (
                        category_matcher.__repr__()))

def do_match_var(parsers, matches, settings):
    if not settings['do_variations']:
        return

    variation_matcher = VariationMatcher()
    variation_matcher.process_registers(
        parsers.slave.variations, parsers.master.variations
    )

    if Registrar.DEBUG_VARS:
        Registrar.register_message("variation matcher:\n%s" %
                                   variation_matcher.__repr__())

    matches.variation.globals.add_matches(variation_matcher.pure_matches)
    matches.variation.masterless.add_matches(
        variation_matcher.masterless_matches)
    matches.variation.deny_anomalous(
        'variation_matcher.masterless_matches',
        variation_matcher.masterless_matches
    )
    matches.variation.slaveless.add_matches(
        variation_matcher.slaveless_matches)
    matches.variation.deny_anomalous(
        'variation_matcher.slaveless_matches',
        variation_matcher.slaveless_matches
    )
    if variation_matcher.duplicate_matches:
        matches.variation.duplicate['index'] = variation_matcher.duplicate_matches


def do_merge_images(matches, parsers, updates, settings):
    updates.image = UpdateNamespace()

    if not hasattr(matches, 'image'):
        return updates

    if Registrar.DEBUG_TRACE:
        print(matches.image.tabulate())

    sync_handles = settings.sync_handles_img

    for match in matches.image.valid:
        m_object = match.m_object
        for s_object in match.s_objects:

            # TODO: implement img mod time check

            sync_update = settings.syncupdate_class_img(m_object, s_object)

            sync_update.update(sync_handles)

            if not sync_update.important_static:
                insort(updates.image.problematic, sync_update)
                continue

            if sync_update.m_updated:
                updates.image.master.append(sync_update)

            if sync_update.s_updated:
                updates.image.slave.append(sync_update)

    for update in updates.image.master:
        old_master = update.old_m_object
        old_master_id = old_master.attachment_indexer(old_master)
        if Registrar.DEBUG_UPDATE:
            Registrar.register_message(
                "performing update < %5s | %5s > = \n%100s, %100s " %
                (update.master_id, update.slave_id,
                 str(update.old_m_object), str(update.old_s_object)))
        if not old_master_id in parsers.master.attachments:
            exc = UserWarning(
                "couldn't fine pkey %s in parsers.master.attachments" %
                update.master_id)
            Registrar.register_error(exc)
            continue
        for col, warnings in update.sync_warnings.items():
            for warning in warnings:
                if not warning['subject'] == update.master_name:
                    continue

                new_val = warning['new_value']
                parsers.master.attachments[old_master_id][col] = new_val

    if settings['auto_create_new']:
        for count, match in enumerate(matches.image.slaveless):
            m_object = match.m_object
            Registrar.register_message(
                "will create image %d: %s" % (
                    count, m_object.identifier
                )
            )
            if not (m_object.attaches.products or m_object.attaches.categories):
                continue
            # gen_data = m_object.to_dict()
            # core_data = settings.coldata_class_img.translate_data_from(gen_data, settings.coldata_gen_target_write)
            # slave_writable_handles = \
            # settings.coldata_class_img.get_handles_property_defaults(
            #     'write', settings.coldata_img_target_write
            # )
            # # make an exception for file_path
            # for handle in core_data.keys():
            #     if handle == 'file_path':
            #         continue
            #     if (handle not in sync_handles):
            #         del core_data[handle]
            #         continue
            #     slave_writable = slave_writable_handles.get(handle)
            #     if not slave_writable:
            #         del core_data[handle]
            # # api_data = settings.coldata_class_img.translate_data_to(core_data, settings.coldata_img_target)
            sync_update = settings.syncupdate_class_img(m_object)
            sync_update.update(sync_handles)
            updates.image.new_slaves.append(sync_update)

    return updates

def do_merge_categories(matches, parsers, updates, settings):
    updates.category = UpdateNamespace()

    if not hasattr(matches, 'category'):
        return updates

    sync_handles = settings.sync_handles_cat

    for match in matches.category.valid:
        s_object = match.s_object
        for m_object in match.m_objects:
            # m_object = match.m_objects[0]

            sync_update = settings.syncupdate_class_cat(m_object, s_object)

            sync_update.update(sync_handles)

            if not sync_update.important_static:
                insort(updates.category.problematic, sync_update)
                continue

            if sync_update.m_updated:
                updates.category.master.append(sync_update)

            if sync_update.s_updated:
                updates.category.slave.append(sync_update)

    for update in updates.category.master:
        if Registrar.DEBUG_UPDATE:
            Registrar.register_message(
                "performing update < %5s | %5s > = \n%100s, %100s " %
                (update.master_id, update.slave_id,
                 str(update.old_m_object), str(update.old_s_object)))
        if not update.master_id in parsers.master.categories:
            exc = UserWarning(
                "couldn't fine pkey %s in parsers.master.categories" %
                update.master_id)
            Registrar.register_error(exc)
            continue
        for col, warnings in update.sync_warnings.items():
            for warning in warnings:
                if not warning['subject'] == update.master_name:
                    continue

                new_val = warning['new_value']
                parsers.master.categories[update.master_id][col] = new_val

    if settings['auto_create_new']:
        for count, match in enumerate(matches.category.slaveless):
            m_object = match.m_object
            Registrar.register_message(
                "will create category %d: %s" % (
                    count, m_object.identifier
                )
            )
            sync_update = settings.syncupdate_class_cat(m_object)
            updates.category.new_slaves.append(sync_update)

    return updates

def do_merge_prod(matches, parsers, updates, settings):
    """For a given list of matches, return a description of updates required to merge them."""

    if settings.do_variations:
        updates.variation = UpdateNamespace()

    if not settings['do_sync']:
        return

    # Merge products

    sync_handles = settings.sync_handles_prod

    if Registrar.DEBUG_UPDATE:
        Registrar.register_message("sync_handles: %s" % repr(sync_handles))

    for _, prod_match in enumerate(matches.globals):
        if Registrar.DEBUG_CATS or Registrar.DEBUG_VARS:
            Registrar.register_message("processing prod_match: %s" %
                                       prod_match.tabulate())
        m_object = prod_match.m_object
        s_object = prod_match.s_object


        sync_update = settings.syncupdate_class_prod(m_object, s_object)

        # , "gcs %s is not variation but object is" % repr(gcs)
        assert not m_object.is_variation
        # , "gcs %s is not variation but object is" % repr(gcs)
        assert not s_object.is_variation

        sync_update.update(sync_handles)

        # print sync_update.tabulate()

        if settings['do_categories']:

            update_params = {
                'handle': 'category_ids',
                'subject': sync_update.slave_name
            }

            master_cat_ids = set([
                master_category.wpid
                for master_category in m_object.categories.values()
                if master_category.wpid
            ])
            slave_cat_ids = set([
                slave_category.wpid
                for slave_category in s_object.categories.values()
                if slave_category.wpid
            ])

            if Registrar.DEBUG_CATS:
                Registrar.register_message(
                    "comparing categories of %s:\n%s\n%s\n%s\n%s" %
                    (m_object.codesum, str(m_object.categories.values()),
                     str(s_object.categories.values()),
                     str(master_cat_ids), str(slave_cat_ids), ))

            sync_update.old_m_object_core['category_ids'] = list(master_cat_ids)
            sync_update.old_s_object_core['category_ids'] = list(slave_cat_ids)
            update_params['new_value'] = sync_update.old_m_object_core['category_ids']
            update_params['old_value'] = sync_update.old_s_object_core['category_ids']
            # update_params['new_value'] = [
            #     dict(id=category_id) for category_id in master_cat_ids
            # ]
            # update_params['old_value'] = [
            #     dict(id=category_id) for category_id in master_cat_ids
            # ]

            match_index = prod_match.singular_index
            product_category_matches = matches.category.prod.get(match_index)
            if product_category_matches and any([
                product_category_matches.slaveless,
                product_category_matches.masterless
            ]):
                assert \
                    master_cat_ids != slave_cat_ids, \
                    (
                        "if change_match_list exists, then master_cat_ids "
                         "should not equal slave_cat_ids.\n"
                         "This might mean that you have not correctly created "
                         "the new products which need to be created. "
                         "master_cat_ids: %s\n"
                         "slave_cat_ids: %s\n"
                         "change_match_list: \n%s"
                    ) % (
                        master_cat_ids,
                        slave_cat_ids,
                        product_category_matches.tabulate()
                    )
                update_params['reason'] = 'updating'

                sync_update.loser_update(**update_params)
            else:
                assert\
                    master_cat_ids == slave_cat_ids, \
                    "should equal, %s | %s" % (
                        repr(master_cat_ids),
                        repr(slave_cat_ids)
                    )
                update_params['reason'] = 'identical'
                sync_update.tie_update(**update_params)

        # Assumes that GDrive is read only, doesn't care about master
        # updates
        if not sync_update.s_updated:
            continue

        if Registrar.DEBUG_UPDATE:
            Registrar.register_message("sync updates:\n%s" %
                                       sync_update.tabulate())

        if sync_update.s_updated and sync_update.s_deltas:
            insort(updates.delta_slave, sync_update)

        if not sync_update.important_static:
            insort(updates.problematic, sync_update)
            continue

        if sync_update.s_updated:
            insort(updates.slave, sync_update)

    if settings['auto_create_new']:
        for new_prod_count, new_prod_match in enumerate(matches.slaveless):

            m_object = new_prod_match.m_object
            Registrar.register_message(
                "will create product %d: %s" % (
                    new_prod_count, m_object.identifier
                )
            )
            sync_update = settings.syncupdate_class_prod(m_object)
            sync_update.update(sync_handles)
            updates.category.new_slaves.append(
                sync_update
            )

def do_merge_var(matches, parsers, updates, settings):
    if not settings['do_variations']:
        return

    sync_handles = settings.sync_handles_var

    if matches.variation.duplicate:
        exc = UserWarning(
            "variations couldn't be synchronized because of ambiguous SKUs:%s"
            % '\n'.join(map(str, matches.variation.duplicate)))
        Registrar.register_error(exc)
        raise exc

    for var_match_count, var_match in enumerate(matches.variation.globals):
        # print "processing var_match: %s" % var_match.tabulate()
        m_object = var_match.m_object
        s_object = var_match.s_object

        sync_update = settings.syncupdate_class_var(m_object, s_object)

        sync_update.update(sync_handles)

        # Assumes that GDrive is read only, doesn't care about master
        # updates
        if not sync_update.s_updated:
            continue

        if Registrar.DEBUG_VARS:
            Registrar.register_message("var update %d:\n%s" % (
                var_match_count, sync_update.tabulate()))

        if not sync_update.important_static:
            insort(updates.variation.problematic, sync_update)
            continue

        if sync_update.s_updated:
            insort(updates.variation.slave, sync_update)

    for var_match_count, var_match in enumerate(
            matches.variation.slaveless):
        assert var_match.has_no_slave
        m_object = var_match.m_object

        # sync_update = SyncUpdateVarWoo(m_object, None)

        # sync_update.update()

        if Registrar.DEBUG_VARS:
            Registrar.register_message("var create %d:\n%s" % (
                var_match_count, m_object.identifier))

        # TODO: figure out which attribute terms to add

    for var_match_count, var_match in enumerate(
            matches.variation.masterless):
        assert var_match.has_no_master
        s_object = var_match.s_object

        # sync_update = SyncUpdateVarWoo(None, s_object)

        # sync_update.update()

        if Registrar.DEBUG_VARS:
            Registrar.register_message("var delete: %d:\n%s" % (
                var_match_count, s_object.identifier))

        # TODO: figure out which attribute terms to delete

    if settings['auto_create_new']:
        # TODO: auto create new variations
        raise NotImplementedError()

def do_report_images(reporters, matches, updates, parsers, settings):
    raise NotImplementedError()
    # TODO: this

def do_report_categories(reporters, matches, updates, parsers, settings):
    Registrar.register_progress("Write Categories Report")

    do_cat_sync_gruop(reporters.cat, matches, updates, parsers, settings)

    if reporters.cat:
        reporters.cat.write_document_to_file('cat', settings.rep_cat_path)

    return reporters

    # with io.open(settings.rep_cat_path, 'w+', encoding='utf8') as res_file:
    #     reporter = HtmlReporter()
    #
    #     syncing_group = HtmlReporter.Group('cats',
    #                                        'Category Syncing Results')
    #
    #     # TODO: change this to change this to updates.category.prod
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.delete_slave'),
    #     #         description="%s items will leave categories" %
    #     #         settings.slave_name,
    #     #         data=tabulate(
    #     #             [
    #     #                 [
    #     #                     index,
    #     #                     # parsers.slave.products[index],
    #     #                     # parsers.slave.products[index].categories,
    #     #                     # ", ".join(category.cat_name \
    #     #                     # for category in matches_.merge().m_objects),
    #     #                     ", ".join([
    #     #                         category_.cat_name
    #     #                         for category_ in matches_.merge().s_objects
    #     #                     ])
    #     #                 ] for index, matches_ in matches.category.delete_slave.items()
    #     #             ],
    #     #             tablefmt="html"),
    #     #         length=len(matches.category.delete_slave)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     # TODO: change this to change this to updates.category.prod
    #     # matches.category.delete_slave_ns_data = tabulate(
    #     #     [
    #     #         [
    #     #             index,
    #     #             ", ".join([
    #     #                 category_.cat_name
    #     #                 for category_ in matches_.merge().s_objects
    #     #                 if not re.search('Specials', category_.cat_name)
    #     #             ])
    #     #         ] for index, matches_ in matches.category.delete_slave.items()
    #     #     ],
    #     #     tablefmt="html"
    #     # )
    #     #
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.delete_slave_not_specials'),
    #     #         description="%s items will leave categories" %
    #     #         settings.slave_name,
    #     #         data=matches.category.delete_slave_ns_data,
    #     #         length=len(matches.category.delete_slave)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     # TODO: change this to updates.category.prod
    #     # syncing_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('matches.category.slaveless'),
    #     #         description="%s items will join categories" %
    #     #         settings.slave_name,
    #     #         data=tabulate(
    #     #             [
    #     #                 [
    #     #                     index,
    #     #                     # parsers.slave.products[index],
    #     #                     # parsers.slave.products[index].categories,
    #     #                     ", ".join([
    #     #                         category_.cat_name
    #     #                         for category_ in matches_.merge()
    #     #                         .m_objects
    #     #                     ]),
    #     #                     # ", ".join(category_.cat_name \
    #     #                     # for category_ in matches_.merge().s_objects)
    #     #                 ] for index, matches_ in matches.category.slaveless.items()
    #     #             ],
    #     #             tablefmt="html"),
    #     #         length=len(matches.category.slaveless)
    #     #         # data = '<hr>'.join([
    #     #         #         "%s<br/>%s" % (index, match.tabulate(tablefmt="html")) \
    #     #         #         for index, match in matches.category.delete_slave.items()
    #     #         #     ]
    #     #         # )
    #     #     ))
    #
    #     reporter.add_group(syncing_group)
    #
    # if not reporter.groups:
    #     empty_group = HtmlReporter.Group('empty', 'Nothing to report')
    #     # empty_group.add_section(
    #     #     HtmlReporter.Section(
    #     #         ('empty'),
    #     #         data = ''
    #     #
    #     #     )
    #     # )
    #     Registrar.register_message('nothing to report')
    #     reporter.add_group(empty_group)
    #
    # res_file.write(reporter.get_document_unicode())


def do_report(reporters, matches, updates, parsers, settings):
    """ Write report of changes to be made. """

    if not settings.get('do_report'):
        return reporters

    Registrar.register_progress("Write Report")

    do_main_summary_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_delta_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_sync_group(
        reporters.main, matches, updates, parsers, settings
    )
    do_variation_sync_group(
        reporters.main, matches, updates, parsers, settings
    )

    if reporters.main:
        reporters.main.write_document_to_file('main', settings.rep_main_path)

    if settings.get('report_matching'):
        Registrar.register_progress("Write Matching Report")

        do_matches_summary_group(
            reporters.match, matches, updates, parsers, settings
        )
        do_matches_group(
            reporters.match, matches, updates, parsers, settings
        )
        if settings.do_variations:
            do_variation_matches_group(
                reporters.match, matches, updates, parsers, settings
            )
        if settings.do_categories:
            do_category_matches_group(
                reporters.match, matches, updates, parsers, settings
            )

        if reporters.match:
            reporters.match.write_document_to_file(
                'match', settings.rep_match_path)

    return reporters

def do_report_post(reporters, results, settings):
    """ Reports results from performing updates."""
    raise NotImplementedError()

def handle_failed_update(update, results, exc, settings, source=None):
    """Handle a failed update."""
    fail = (update, exc)
    if source == settings.master_name:
        pkey = update.master_id
        results.fails_master.append(fail)
    elif source == settings.slave_name:
        pkey = update.slave_id
        results.fails_slave.append(fail)
    else:
        pkey = ''
    Registrar.register_error(
        "ERROR UPDATING %s (%s): %s\n%s\n%s" % (
            source or '',
            pkey,
            repr(exc),
            update.tabulate(),
            traceback.format_exc()
        )
    )

    if Registrar.DEBUG_TRACE:
        import pudb
        pudb.set_trace()

def usr_prompt_continue(settings):
        input(
            "Please read reports and press Enter to continue or ctrl-c to stop..."
        )

def upload_new_images(parsers, results, settings, client, new_updates):

    if not (new_updates and settings['update_slave']):
        return

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(new_updates), items_plural='new %s' % client.endpoint_plural
        )

    # sync_handles = settings.sync_handles_img

    update_count = 0

    while new_updates:

        sync_update = new_updates.pop(0)

        core_data = sync_update.get_slave_updates()

        if Registrar.DEBUG_UPDATE:
            Registrar.register_message("uploading new image (core format): %s" % pformat(core_data))

        update_count += 1
        if Registrar.DEBUG_PROGRESS:
            update_progress_counter.maybe_print_update(update_count)

        try:
            response = client.create_item_core(core_data)
            response_api_data = response.json()
        except BaseException as exc:
            handle_failed_update(
                sync_update, results, exc, settings, settings.slave_name
            )
            continue
        if client.page_nesting:
            response_api_data = response_api_data[client.endpoint_singular]

        response_gen_object = parsers.slave.analyse_api_image_raw(response_api_data)

        sync_update.set_new_s_object_gen(response_gen_object)

        if Registrar.DEBUG_IMG:
            Registrar.register_message(
                "image being updated with parser data: %s"
                % pformat(response_gen_object))

        sync_update.set_new_s_object_gen(response_gen_object)
        sync_update.old_m_object_gen.update(response_gen_object)

        results.successes.append(sync_update)


def upload_image_changes(parsers, results, settings, client, change_updates):

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(change_updates), items_plural='%s updates' % client.endpoint_singular
        )

    if not settings['update_slave']:
        return

    for count, sync_update in enumerate(change_updates):
        if Registrar.DEBUG_PROGRESS:
            update_progress_counter.maybe_print_update(count)

        if not sync_update.s_updated:
            continue

        try:
            pkey = sync_update.slave_id
            changes = sync_update.get_slave_updates()
            response_raw = client.upload_changes_core(pkey, changes)
            response_api_data = response_raw.json()
        except Exception as exc:
            handle_failed_update(
                sync_update, results, exc, settings, settings.slave_name
            )
            continue

        response_core_data = settings.coldata_class_img.translate_data_from(
            response_api_data, settings.coldata_img_target
        )
        response_gen_data = settings.coldata_class_img.translate_data_to(
            response_core_data, settings.coldata_gen_target_write
        )

        sync_update.old_s_object_gen.update(response_gen_data)
        sync_update.set_new_s_object_gen(sync_update.old_s_object_gen)
        sync_update.old_m_object_gen.update(response_gen_data)

        results.successes.append(sync_update)


def do_updates_images(updates, parsers, results, settings):
    """Perform a list of updates on attachments."""

    results.image = ResultsNamespace()
    results.image.new = ResultsNamespace()

    sync_client_class = settings.slave_img_sync_client_class
    sync_client_args = settings.slave_img_sync_client_args

    # updates in which an item is modified
    change_updates = updates.image.slave
    if settings.do_problematic:
        change_updates += updates.image.problematic
    # updates in which a new item is created
    new_updates = []
    if settings['auto_create_new']:
        new_updates += updates.image.new_slaves
    else:
        for update in new_updates:
            new_item_api = update.get_slave_updates_native()
            exc = UserWarning("{0} needs to be created: {1}".format(
                sync_client_class.endpoint_singular, new_item_api
            ))
            Registrar.register_warning(exc)
    Registrar.register_progress("Changing {1} {0} and creating {2} {0}".format(
        sync_client_class.endpoint_plural, len(change_updates), len(new_updates)
    ))

    if not (new_updates or change_updates):
        return

    if settings['ask_before_update']:
        usr_prompt_continue(settings)

    with sync_client_class(**sync_client_args) as client:
        if Registrar.DEBUG_IMG:
            Registrar.register_message("created img client")

        if new_updates:
            # create attachments that do not yet exist on slave
            upload_new_images(
                parsers, results.image.new, settings, client, new_updates
            )

        if change_updates:
            upload_image_changes(
                parsers, results.image, settings, client, change_updates
            )

def upload_new_categories(parsers, results, settings, client, new_updates):
    """
    Create new categories in client in an order which creates parents first.
    """
    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(new_updates), items_plural='new %s' % client.endpoint_plural
        )

    if not (new_updates and settings['update_slave']):
        return

    sync_handles = settings.sync_handles_cat

    update_count = 0

    while new_updates:

        sync_update = new_updates.pop(0)
        new_object_gen = sync_update.old_m_object_gen

        if Registrar.DEBUG_CATS:
            Registrar.register_message("new category %s" %
                                       new_object_gen)

        # make sure parent updates are done before children

        if new_object_gen.parent:
            remaining_m_objects = set([
                sync_update.old_m_object_gen for update_ in new_updates
            ])
            parent = new_object_gen.parent
            if not parent.is_root and parent in remaining_m_objects:
                new_updates.append(sync_update)
                continue

        # have to refresh sync_update to get parent wpid
        sync_update.set_old_m_object_gen(sync_update.old_m_object)
        sync_update.update(sync_handles)

        core_data = sync_update.get_slave_updates()

        if Registrar.DEBUG_UPDATE:
            Registrar.register_message("uploading new category (api format): %s" % pformat(core_data))

        update_count += 1
        if Registrar.DEBUG_PROGRESS:
            update_progress_counter.maybe_print_update(update_count)

        try:
            response = client.create_item_core(core_data)
            response_api_data = response.json()
        except BaseException as exc:
            handle_failed_update(
                sync_update, results, exc, settings, settings.slave_name
            )
            continue
        if client.page_nesting:
            response_api_data = response_api_data[client.endpoint_singular]

        response_gen_object = parsers.slave.process_api_category_raw(response_api_data)

        sync_update.set_new_s_object_gen(response_gen_object)

        if Registrar.DEBUG_CATS:
            Registrar.register_message(
                "category being updated with parser data: %s"
                % pformat(response_gen_object))

        sync_update.old_m_object_gen.update(response_gen_object)

        results.successes.append(sync_update)

def upload_category_changes(parsers, results, settings, client, change_updates):
    """
    Upload a list of category changes
    """

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(change_updates), items_plural='category updates'
        )

    if not settings['update_slave']:
        return

    for count, sync_update in enumerate(change_updates):
        if Registrar.DEBUG_PROGRESS:
            update_progress_counter.maybe_print_update(count)

        if not sync_update.s_updated:
            continue

        try:
            pkey = sync_update.slave_id
            changes = sync_update.get_slave_updates_native()
            response_raw = client.upload_changes(pkey, changes)
            response_api_data = response_raw.json()
        except Exception as exc:
            handle_failed_update(
                sync_update, results, exc, settings, settings.slave_name
            )
            continue

        response_core_data = settings.coldata_class_cat.translate_data_from(
            response_api_data, settings.coldata_cat_target
        )
        response_gen_data = settings.coldata_class_cat.translate_data_to(
            response_core_data, settings.coldata_gen_target_write
        )

        if Registrar.DEBUG_CATS:
            Registrar.register_message(
                "category being updated with parser data: %s"
                % pformat(response_gen_data))

        sync_update.old_s_object_gen.update(response_gen_data)
        sync_update.set_new_s_object_gen(sync_update.old_s_object_gen)
        sync_update.old_m_object_gen.update(response_gen_data)

        results.successes.append(sync_update)


def do_updates_categories(updates, parsers, results, settings):
    """Perform a list of updates on categories."""
    if not hasattr(updates, 'category'):
        return

    results.category = ResultsNamespace()
    results.category.new = ResultsNamespace()

    sync_client_class = settings.slave_cat_sync_client_class
    sync_client_args = settings.slave_cat_sync_client_args

    # updates in which an item is modified
    change_updates = updates.category.slave
    if settings.do_problematic:
        change_updates += updates.category.problematic
    # updates in which a new item is created
    new_updates = []
    if settings['auto_create_new']:
        new_updates += updates.category.new_slaves
    else:
        for update in new_updates:
            new_item_api = update.get_slave_updates_native()
            exc = UserWarning("{0} needs to be created: {1}".format(
                sync_client_class.endpoint_plural, new_item_api
            ))
            Registrar.register_warning(exc)
    Registrar.register_progress("Changing {1} {0} and creating {2} {0}".format(
        sync_client_class.endpoint_plural, len(change_updates), len(new_updates)
    ))

    if not (new_updates or change_updates):
        return

    if settings['ask_before_update']:
        usr_prompt_continue(settings)

    with sync_client_class(**sync_client_args) as client:
        if Registrar.DEBUG_CATS:
            Registrar.register_message("created cat client")

        if new_updates:
            # create categories that do not yet exist on slave
            upload_new_categories(
                parsers, results.category.new, settings, client, new_updates
            )

        if change_updates:
            upload_category_changes(
                parsers, results.category, settings, client, change_updates
            )

def upload_new_products(parsers, results, settings, client, new_updates):
    """
    Create new products in client in an order which creates parents first.
    """
    raise NotImplementedError()

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(new_updates), items_plural='new %s' % client.endpoint_plural
        )

    if not (new_updates and settings['update_slave']):
        return

def upload_product_changes(parsers, results, settings, client, change_updates):
    raise NotImplementedError()

    if Registrar.DEBUG_PROGRESS:
        update_progress_counter = ProgressCounter(
            len(change_updates), items_plural='product updates'
        )

    if not settings['update_slave']:
        return

    for count, sync_update in enumerate(change_updates):
        if Registrar.DEBUG_PROGRESS:
            update_progress_counter.maybe_print_update(count)

        if sync_update.s_updated:
            try:
                pkey = sync_update.slave_id
                changes = sync_update.get_slave_updates_native()
                client.upload_changes(pkey, changes)
            except Exception as exc:
                handle_failed_update(
                    sync_update, results, exc, settings, settings.slave_name
                )

def do_updates_prod(updates, parsers, settings, results):
    """
    Update products in slave.
    """
    # updates in which an item is modified

    results.new = ResultsNamespace()
    slave_client_class = settings.slave_sync_client_class
    slave_client_args = settings.slave_sync_client_args

    change_updates = updates.slave
    if settings.do_problematic:
        change_updates += updates.problematic
    # updates in which a new item is created
    new_updates = []
    if settings['auto_create_new']:
        new_updates += updates.new_slaves
    else:
        for update in new_updates:
            new_item_api = update.get_slave_updates_native()
            exc = UserWarning("{0} needs to be created: {1}".format(
                slave_client_class.endpoint_singular, new_item_api
            ))
            Registrar.register_warning(exc)
    Registrar.register_progress("Changing {1} {0} and creating {2} {0}".format(
        slave_client_class.endpoint_plural, len(change_updates), len(new_updates)
    ))

    if not (new_updates or change_updates):
        return

    if settings['ask_before_update']:
        usr_prompt_continue(settings)


    with slave_client_class(**slave_client_args) as client:
        if new_updates:
            upload_new_products(
                parsers, results, settings, client, new_updates
            )
        if change_updates:
            upload_product_changes(
                parsers, results, settings, client, change_updates
            )

def do_updates_var(updates, parsers, settings, results):
    raise NotImplementedError()

    change_updates = updates.variation.slave
    if settings.do_problematic:
        change_updates += updates.variation.problematic

    if not change_updates:
        return


def main(override_args=None, settings=None):
    """Main function for generator."""
    if not settings:
        settings = SettingsNamespaceProd()
    settings.init_settings(override_args)

    settings.init_dirs()

    ########################################
    # Create Product Parser object
    ########################################

    parsers = ParserNamespace()
    populate_master_parsers(parsers, settings)

    check_warnings(settings)

    if settings.schema_is_woo and settings.do_images:
        process_images(settings, parsers)

    if parsers.master.objects:
        export_master_parser(settings, parsers)

    if settings.master_and_quit:
        sys.exit(ExitStatus.success)

    populate_slave_parsers(parsers, settings)

    if parsers.slave.objects:
        cache_api_data(settings, parsers)

    matches = MatchNamespace(
        index_fn=ProductMatcher.product_index_fn
    )
    updates = UpdateNamespace()
    reporters = ReporterNamespace()
    results = ResultsNamespace()

    if settings.do_images:
        do_match_images(parsers, matches, settings)
        do_merge_images(matches, parsers, updates, settings)
        do_report_images(
            reporters, matches, updates, parsers, settings
        )
        check_warnings(settings)
        if not settings.report_and_quit:
            try:
                do_updates_images(updates, parsers, results, settings)
            except (SystemExit, KeyboardInterrupt):
                return reporters, results

    if settings.do_categories:

        do_match_categories(parsers, matches, settings)
        do_merge_categories(matches, parsers, updates, settings)
        do_report_categories(
            reporters, matches, updates, parsers, settings
        )
        check_warnings(settings)
        if not settings.report_and_quit:
            try:
                do_updates_categories(updates, parsers, results, settings)
            except (SystemExit, KeyboardInterrupt):
                return reporters, results

    raise UserWarning("end of completed functions")

    do_match_prod(parsers, matches, settings)
    do_merge_prod(matches, parsers, updates, settings)
    do_merge_var(matches, parsers, updates, settings)
    # check_warnings(settings)
    do_report(reporters, matches, updates, parsers, settings)

    if settings.report_and_quit:
        sys.exit(ExitStatus.success)

    check_warnings()

    Registrar.register_message(
        "pre-sync summary: \n%s" % reporters.main.get_summary_text()
    )

    try:
        do_updates_prod(updates, parsers, settings, results)
    except (SystemExit, KeyboardInterrupt):
        return reporters, results
    if settings['do_variations']:
        try:
            do_updates_var(updates, parsers, settings, results)
        except (SystemExit, KeyboardInterrupt):
            return reporters, results
    do_report_post(reporters, results, settings)

    Registrar.register_message(
        "post-sync summary: \n%s" % reporters.post.get_summary_text()
    )

    #########################################
    # Display reports
    #########################################

    Registrar.register_progress("Displaying reports")

    if settings.do_report:
        if settings['rep_web_path']:
            shutil.copyfile(settings.rep_main_path, settings['rep_web_path'])
            if settings['web_browser']:
                os.environ['BROWSER'] = settings['web_browser']
                # print "set browser environ to %s" % repr(web_browser)
            # print "moved file from %s to %s" % (settings.rep_main_path,
            # repWeb_path)

            webbrowser.open(settings['rep_web_link'])
    else:
        print "open this link to view report %s" % settings['rep_web_link']


def catch_main(override_args=None):
    """Run the main function within a try statement and attempt to analyse failure."""
    file_path = __file__
    cur_dir = os.getcwd() + '/'
    if file_path.startswith(cur_dir):
        file_path = file_path[len(cur_dir):]
    override_args_repr = ''
    if override_args is not None:
        override_args_repr = ' '.join(override_args)

    full_run_str = "%s %s %s" % (
        str(sys.executable), str(file_path), override_args_repr)

    settings = SettingsNamespaceProd()

    status = 0
    try:
        main(settings=settings, override_args=override_args)
    except SystemExit:
        status = ExitStatus.failure
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        status = 1
        if isinstance(exc, UserWarning):
            status = 65
        elif isinstance(exc, IOError):
            status = 74
            print( "cwd: %s" % os.getcwd() )
        elif exc.__class__ in ["ReadTimeout", "ConnectionError", "ConnectTimeout", "ServerNotFoundError"]:
            status = 69  # service unavailable

        if status:
            Registrar.register_error(traceback.format_exc())
            Registrar.raise_exception(exc)

    with io.open(settings.log_path, 'w+', encoding='utf8') as log_file:
        for source, messages in Registrar.get_message_items(1).items():
            print source
            log_file.writelines([SanitationUtils.coerce_unicode(source)])
            log_file.writelines([
                SanitationUtils.coerce_unicode(message) for message in messages
            ])
            for message in messages:
                pprint(message, indent=4, width=80, depth=2)

    #########################################
    # zip reports
    #########################################

    files_to_zip = [
        settings.rep_fail_master_csv_path, settings.rep_fail_slave_csv_path, settings.rep_main_path
    ]

    with zipfile.ZipFile(settings.zip_path, 'w') as zip_file:
        for file_to_zip in files_to_zip:
            try:
                os.stat(file_to_zip)
                zip_file.write(file_to_zip)
            except BaseException:
                pass
        Registrar.register_message('wrote file %s' % zip_file.filename)

    # print "\nexiting with status %s \n" % status
    if status:
        print "re-run with: \n%s" % full_run_str
    else:
        Registrar.register_message("re-run with:\n%s" % full_run_str)

    sys.exit(status)


if __name__ == '__main__':
    catch_main()
