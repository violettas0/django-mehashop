from rest_framework import serializers
from pydantic import BaseModel
from .models import Product, Category, Cart, CartItem, Order

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'image', 'price', 'category', 'attributes']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'created_at']

class PaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    confirmation_url = serializers.URLField(required=False)
    payment_status = serializers.CharField(required=False)



class ProductFilter(BaseModel):
    category_id: int | None
    min_price: float | None
    max_price: float | None
    sort_by: str = "price"