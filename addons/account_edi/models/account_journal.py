# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    edi_format_ids = fields.Many2many(comodel_name='account.edi.format',
                                      string='Electronic invoicing',
                                      help='Send XML/EDI invoices',
                                      domain="[('id', 'in', compatible_edi_ids)]",
                                      compute='_compute_edi_format_ids',
                                      readonly=False, store=True)

    compatible_edi_ids = fields.Many2many(comodel_name='account.edi.format',
                                          compute='_compute_compatible_edi_ids',
                                          help='EDI format that support moves in this journal')

    def write(self, vals):
        # OVERRIDE
        # Don't allow the user to deactivate an edi format having at least one document to be processed.
        if vals.get('edi_format_ids'):
            old_edi_format_ids = self.edi_format_ids
            res = super().write(vals)
            diff_edi_format_ids = old_edi_format_ids - self.edi_format_ids
            documents = self.env['account.edi.document'].search([
                ('move_id.journal_id', 'in', self.ids),
                ('edi_format_id', 'in', diff_edi_format_ids.ids),
                ('state', 'in', ('to_cancel', 'to_send')),
            ])
            # If the formats we are unchecking do not need a webservice, we don't need them to be correctly sent
            if documents.filtered(lambda d: d.edi_format_id._needs_web_services()):
                raise UserError(_('Cannot deactivate (%s) on this journal because not all documents are synchronized', ', '.join(documents.edi_format_id.mapped('display_name'))))
            # remove these documents which: do not need a web service & are linked to the edi formats we are unchecking
            if documents:
                documents.unlink()
            return res
        else:
            return super().write(vals)

    @api.depends('type', 'company_id', 'company_id.country_id')
    def _compute_compatible_edi_ids(self):
        edi_formats = self.env['account.edi.format'].search([])

        for journal in self:
            compatible_edis = edi_formats.filtered(lambda e: e._is_compatible_with_journal(journal))
            journal.compatible_edi_ids += compatible_edis

    @api.depends('type', 'company_id', 'company_id.country_id')
    def _compute_edi_format_ids(self):
        edi_formats = self.env['account.edi.format'].search([])

        for journal in self:
            journal.edi_format_ids += edi_formats.filtered(lambda e: e._is_compatible_with_journal(journal))
