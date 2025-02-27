# marketplace/models.py
from django.db import models

from accounts.models import User
from store.models import ProductItem

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    productitem = models.ForeignKey(ProductItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.user
