import json
import base64

from odoo import models, fields, api, _
import requests


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def init_knowit_sign(self):
        url = "http://localhost:8102"
        username = "Skogsstyrelsen"
        password = "password"
        b64_auth = base64.b64encode(bytes(f"{username}:{password}", "utf-8"))
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {b64_auth.decode()}"
        }
        data = {

        }
        req = requests.request("POST", url=url, data=json.dumps(data), headers=headers)
        print(req)

