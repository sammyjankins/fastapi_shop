import os

import redis

from apps.product.models import get_product_by_id

r = redis.Redis(host=os.environ.get('REDIS_HOST'),
                port=os.environ.get('REDIS_PORT'),
                db=os.environ.get('REDIS_DB'))


class Recommender:

    def __init__(self, product_ids):
        self.product_ids = product_ids

    def get_product_key(self, id):
        return f'product:{id}:purchased_with'

    def products_bought(self):
        for product_id in self.product_ids:
            for with_id in self.product_ids:
                if product_id != with_id:
                    r.zincrby(self.get_product_key(product_id), 1, with_id)

    async def suggest_products_for(self, max_results=6):

        if len(self.product_ids) == 1:
            suggestions = r.zrange(
                self.get_product_key(self.product_ids[0]),
                0, -1, desc=True)[:max_results]
        else:
            flat_ids = ''.join([_id for _id in self.product_ids])
            tmp_key = f'tmp_{flat_ids}'

            product_keys = [self.get_product_key(id) for id in self.product_ids]
            r.zunionstore(tmp_key, product_keys)

            r.zrem(tmp_key, *self.product_ids)

            suggestions = r.zrange(tmp_key, 0, -1, desc=True)[:max_results]
            r.delete(tmp_key)

        suggested_products = [await get_product_by_id(_id.decode()) for _id in suggestions]
        return suggested_products
