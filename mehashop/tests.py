from django.test import TestCase, Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Cart, CartItem
from .models import Product, Category, Order
import json
import uuid
from unittest.mock import patch, MagicMock, Mock
from decimal import Decimal
from urllib.parse import urlparse, parse_qs
from social_core.exceptions import AuthFailed


User = get_user_model()

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
        """Тест POST-запроса для создания и получения продуктов."""
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
        """Тест GET-запроса для получения детальной информации о продукте."""
        url = reverse('product-detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Норковая шуба")
        self.assertEqual(Decimal(response.data['price']), Decimal('100000.00'))

    def test_get_categories(self):
        """Тест GET-запроса для получения списка категорий."""
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ожидаем 1 категорию
        self.assertEqual(response.data[0]['name'], "Шубы")



class CartAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        # Создаем пользователя и авторизуемся
        self.user = User.objects.create_user(username='testuser', password='testpass')
        # Создаем токен для пользователя
        self.token = Token.objects.create(user=self.user)
        # Настраиваем клиент для отправки запросов с токеном
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        self.cart = Cart.objects.create(user=self.user)
        self.product = Product.objects.create(name="Шуба", price=100000.00)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_get_cart(self):
        """Тест GET-запроса для получения содержимого корзины."""
        url = reverse('cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Ожидаем 1 товар в корзине
        self.assertEqual(response.data[0]['product']['name'], "Шуба")

    def test_post_order(self):
        """Тест POST-запроса для создания заказа из корзины."""
        url = reverse('order-create')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)  # Проверяем, что заказ создан
        self.assertEqual(CartItem.objects.count(), 0)  # Проверяем, что корзина пуста



class CreatePaymentViewTest(TestCase):
    def setUp(self):
        # Создаем пользователя
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Создаем тестовый заказ
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            status='created'
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Создаем тестовый положительный запрос
        self.successful_payment_response = {
            'id': 'test_payment_id',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.yookassa.ru/confirmation'
            }
        }

    @patch('requests.post')
    def test_create_payment_success(self, mock_post):
        """Тест успешного создания платежа."""
        # Настройка мока для ответа
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.successful_payment_response
        mock_post.return_value = mock_response

        # Выполнение запроса
        url = reverse('create-payment', kwargs={'order_id': self.order.id})
        response = self.client.post(url)

        # Проверки
        self.assertEqual(response.status_code, 200)
        self.assertIn('confirmation_url', response.data)
        self.assertEqual(response.data['confirmation_url'], 'https://test.yookassa.ru/confirmation')

        # Проверка обновления заказа
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_id, 'test_payment_id')
        self.assertEqual(self.order.payment_status, 'pending')
        self.assertEqual(self.order.payment_method, 'YooKassa')

        # Проверка, что запрос был сделан с правильными данными
        called_args = mock_post.call_args
        self.assertEqual(called_args[0][0], 'https://api.yookassa.ru/v3/payments')

        # Проверка данных платежа - исправление для строкового представления Decimal
        payment_data = called_args[1]['json']
        # Вместо прямого сравнения строк, преобразуем оба значения в Decimal для сравнения
        self.assertEqual(Decimal(payment_data['amount']['value']), self.order.total_price)
        self.assertEqual(payment_data['amount']['currency'], 'RUB')
        self.assertTrue(payment_data['capture'])
        self.assertEqual(payment_data['confirmation']['type'], 'redirect')

        # Проверка заголовков
        headers = called_args[1]['headers']
        self.assertEqual(headers['Content-Type'], 'application/json')
        self.assertTrue('Idempotence-Key' in headers)

    @patch('requests.post')
    def test_create_payment_failure(self, mock_post):
        """Тест неудачного создания платежа."""
        # Настройка мока для возврата ошибки
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Invalid payment data'}
        mock_post.return_value = mock_response

        # Выполнение запроса
        url = reverse('create-payment', kwargs={'order_id': self.order.id})
        response = self.client.post(url)

        # Проверки
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data)

        # Проверка, что заказ не был обновлен
        self.order.refresh_from_db()
        self.assertIsNone(getattr(self.order, 'payment_id', None))

    def test_create_payment_order_not_found(self):
        """Тест создания платежа для несуществующего заказа."""
        non_existent_id = 9999
        url = reverse('create-payment', kwargs={'order_id': non_existent_id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_create_payment_unauthorized(self):
        """Тест создания платежа без авторизации."""
        # Используем неавторизованный клиент
        client = APIClient()
        url = reverse('create-payment', kwargs={'order_id': self.order.id})
        response = client.post(url)

        self.assertEqual(response.status_code, 401)

    def test_create_payment_wrong_user(self):
        """Тест создания платежа для заказа другого пользователя."""
        # Создаем другого пользователя и авторизуемся под ним
        other_user = User.objects.create_user(username='otheruser', password='otherpass123')
        client = APIClient()
        client.force_authenticate(user=other_user)

        # Пытаемся получить доступ к заказу первого пользователя
        url = reverse('create-payment', kwargs={'order_id': self.order.id})
        response = client.post(url)

        # Должен вернуть 404, так как заказ фильтруется по пользователю
        self.assertEqual(response.status_code, 404)


class YooKassaWebhookTest(TestCase):
    def setUp(self):
        # Создаем тестового пользователя
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        # Создаем тестовый заказ с payment_id
        self.order = Order.objects.create(
            user=self.user,
            total_price=Decimal('1000.00'),
            status='created',
            payment_id='test_payment_id',
            payment_status='pending'
        )

        # Настроим клиент
        self.client = Client()

    def test_webhook_payment_succeeded(self):
        """Тест обработки webhook для успешного платежа."""
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'test_payment_id',
                'status': 'succeeded'
            }
        }

        url = reverse('yookassa-webhook')
        response = self.client.post(
            url,
            data=json.dumps(webhook_data),
            content_type='application/json'
        )

        # Проверка ответа
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'status': 'ok'})

        # Проверка, что заказ был обновлен
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'succeeded')
        self.assertEqual(self.order.status, 'paid')

    def test_webhook_payment_canceled(self):
        """Тест обработки webhook для отмененного платежа."""
        webhook_data = {
            'event': 'payment.canceled',
            'object': {
                'id': 'test_payment_id',
                'status': 'canceled'
            }
        }

        url = reverse('yookassa-webhook')
        response = self.client.post(
            url,
            data=json.dumps(webhook_data),
            content_type='application/json'
        )

        # Проверка ответа
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'status': 'ok'})

        # Проверка, что заказ был обновлен
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'canceled')
        self.assertEqual(self.order.status, 'canceled')

    def test_webhook_payment_not_found(self):
        """Тест webhook для несуществующего payment_id."""
        webhook_data = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'non_existent_payment_id',
                'status': 'succeeded'
            }
        }

        url = reverse('yookassa-webhook')
        response = self.client.post(
            url,
            data=json.dumps(webhook_data),
            content_type='application/json'
        )

        # Проверка ответа
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {'error': 'Заказ не найден'})

    def test_webhook_invalid_method(self):
        """Тест webhook для GET запроса."""
        url = reverse('yookassa-webhook')
        response = self.client.get(url)

        # Проверка ответа
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content), {'error': 'Неверный запрос'})

    def test_webhook_invalid_json(self):
        """Тест webhook с некорректным JSON."""
        url = reverse('yookassa-webhook')
        # Отправляем некорректный JSON, но не ожидаем исключения
        response = self.client.post(
            url,
            data="This is not JSON",
            content_type='application/json'
        )

        # Ожидаем 400 ответ
        self.assertEqual(response.status_code, 400)


class YandexOAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.social_auth_url = reverse('social:begin', args=['yandex-oauth2'])

        # Создаем тестового пользователя
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@yandex.ru',
            password='testpass123'
        )

        # Создаем Site для allauth
        Site.objects.get_or_create(id=1, defaults={'domain': 'localhost', 'name': 'localhost'})

        # Инициализируем OAuth flow и извлекаем state из редиректа
        response = self.client.get(self.social_auth_url, follow=False)
        redirect_url = response['Location']
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        self.state = query_params.get('state', [''])[0]  # Извлекаем state из URL

    def test_login_view_success(self):
        """Тест успешного логина через LoginView"""
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('key', response.json())
        token = Token.objects.get(user=self.test_user)
        self.assertEqual(response.json()['key'], token.key)

    def test_login_view_invalid_credentials(self):
        """Тест логина с неверными данными"""
        login_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.json())
        self.assertEqual(
            response.json()['non_field_errors'][0],
            'Unable to log in with provided credentials.'
        )

    @patch('social_core.backends.oauth.BaseOAuth2.request')
    def test_yandex_oauth_successful_login(self, mock_request):
        """Тест успешной аутентификации через Yandex OAuth"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'token_type': 'bearer',
            'expires_in': 3600,
            'refresh_token': 'test_refresh_token'
        }
        mock_request.return_value = mock_response

        response = self.client.get(self.social_auth_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        callback_response = self.client.get(
            reverse('social:complete', args=['yandex-oauth2']),
            {'code': 'test_code', 'state': self.state}
        )
        self.assertEqual(callback_response.status_code, status.HTTP_302_FOUND)

    @patch('social_core.backends.oauth.BaseOAuth2.request')
    def test_yandex_oauth_invalid_code(self, mock_request):
        """Тест обработки невалидного кода авторизации"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Invalid authorization code'
        }
        mock_request.return_value = mock_response

        response = self.client.get(self.social_auth_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        # Проверяем, что при невалидном коде возникает AuthFailed
        with self.assertRaises(AuthFailed):
            self.client.get(
                reverse('social:complete', args=['yandex-oauth2']),
                {'code': 'invalid_code', 'state': self.state}
            )
        # Примечание: В реальном приложении здесь может быть редирект на страницу ошибки,
        # но в тестовом окружении мы проверяем само исключение

    def test_unauthenticated_access(self):
        """Тест доступа без аутентификации"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(
            self.login_url,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


if __name__ == '__main__':
    import unittest

    unittest.main()