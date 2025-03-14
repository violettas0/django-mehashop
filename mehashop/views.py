from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from requests.auth import HTTPBasicAuth
import requests
import json
import uuid

from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .serializers import ProductSerializer, CategorySerializer, CartItemSerializer, OrderSerializer


# POST /products - получение товаров по категории с фильтрацией и сортировкой
class ProductListView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        category_id = request.data.get('category_id')
        min_price = request.data.get('min_price')
        max_price = request.data.get('max_price')
        sort_by = request.data.get('sort_by', 'price')  # по умолчанию сортировка по цене

        allowed_sort_fields = ['price', 'name', '-price', '-name', 'id', '-id']
        if sort_by not in allowed_sort_fields:
            return Response({"error": "Неправильный параметр сортировки"}, status=status.HTTP_400_BAD_REQUEST)

        products = Product.objects.all()
        if category_id:
            products = products.filter(category_id=category_id)
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)
        products = products.order_by(sort_by)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

# GET /product - получение карточки товара
class ProductDetailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = ProductSerializer(product)
        return Response(serializer.data)

# GET /categories - получение списка категорий
class CategoryListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

# GET, POST, PUT, DELETE /cart - работа с корзиной
class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        items = CartItem.objects.filter(cart=cart)
        serializer = CartItemSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        product = get_object_or_404(Product, id=product_id)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += int(quantity)
            cart_item.save()
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.quantity = quantity
        item.save()
        serializer = CartItemSerializer(item)
        return Response(serializer.data)

    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        item_id = request.data.get('item_id')
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# POST /order - создание заказа
class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        if not cart_items.exists():
            return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=request.user)
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        cart_items.delete()  # Очистка корзины
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.calculate_total_price()

        payment_data = {
            "amount": {"value": str(order.total_price), "currency": "RUB"},
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": "https://yourdomain.com/payment-success"
            },
            "description": f"Оплата заказа №{order.id}"
        }

        idempotence_key = str(uuid.uuid4())

        auth = HTTPBasicAuth(settings.YOOKASSA_AUTH['login'], settings.YOOKASSA_AUTH['secret_key'])

        headers = {
            "Content-Type": "application/json",
            'Idempotence-Key': idempotence_key,
        }

        response = requests.post("https://api.yookassa.ru/v3/payments", json=payment_data, headers=headers, auth=auth)

        if response.status_code == 200:
            data = response.json()
            order.payment_id = data['id']
            order.payment_status = data['status']
            order.payment_method = "YooKassa"
            order.save()
            return Response({"confirmation_url": data['confirmation']['confirmation_url']})
        else:
            return Response({"error": "Ошибка при создании платежа"}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def yookassa_webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)
        payment_id = data.get("object", {}).get("id")
        payment_status = data.get("object", {}).get("status")

        try:
            order = Order.objects.get(payment_id=payment_id)
            order.payment_status = payment_status
            if payment_status == "succeeded":
                order.status = "paid"
            elif payment_status == "canceled":
                order.status = "canceled"
            order.save()
            return JsonResponse({"status": "ok"})
        except Order.DoesNotExist:
            return JsonResponse({"error": "Заказ не найден"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key})
        return Response({"error": "Неправильные данные"}, status=400)

