from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Cart, CartItem
from .models import Product, Category,Order

class ProductAPITest(APITestCase):
    def setUp(self):
        # Инициализация тестового клиента и данных
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Создаем токен для пользователя
        self.token = Token.objects.create(user=self.user)
        # Настраиваем клиент для отправки запросов с токеном
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.category = Category.objects.create(name="Шубы")
        self.product = Product.objects.create(
            name="Норковая шуба",
            description="Элегантная шуба",
            price=100000.00,
            category=self.category
        )


    def test_post_products(self):
        # URL эндпоинта (используем reverse для получения URL по имени)
        url = reverse('product-list')
        # Данные для запроса
        data = {
            'category_id': self.category.id,
            'min_price': 50000.00,
            'max_price': 150000.00,
            'sort_by': 'price'
        }
        # Отправляем POST-запрос
        response = self.client.post(url, data, format='json')
        # Проверяем статус ответа и содержимое
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ожидаем 1 товар
        self.assertEqual(response.data[0]['name'], "Норковая шуба")

    def test_get_product_detail(self):
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Норковая шуба")
        self.assertEqual(response.data['price'], "100000.00")

    def test_get_categories(self):
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ожидаем 1 категорию
        self.assertEqual(response.data[0]['name'], "Шубы")



class CartAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Создаем пользователя и авторизуемся
        # Создаем пользователя
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Создаем токен для пользователя
        self.token = Token.objects.create(user=self.user)
        # Настраиваем клиент для отправки запросов с токеном
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.cart = Cart.objects.create(user=self.user)
        self.product = Product.objects.create(name="Шуба", price=100000.00)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_get_cart(self):
        url = reverse('cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ожидаем 1 товар в корзине
        self.assertEqual(response.data[0]['product']['name'], "Шуба")

    def test_post_order(self):
        url = reverse('order-create')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)  # Проверяем, что заказ создан
        self.assertEqual(CartItem.objects.count(), 0)  # Проверяем, что корзина пуста