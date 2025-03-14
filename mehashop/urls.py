from django.urls import path, include
from dj_rest_auth.views import LogoutView
from .views import (
    ProductListView, ProductDetailView, CategoryListView, CartView, OrderCreateView,
    CreatePaymentView, yookassa_webhook, LoginView
)

urlpatterns = [
    path('products/', ProductListView.as_view(), name='product-list'),
    path('product/<int:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('cart/', CartView.as_view(), name='cart'),
    path('order/', OrderCreateView.as_view(), name='order-create'),

    # Платежи
    path('payment/<int:order_id>/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment/webhook/yookassa/', yookassa_webhook, name='yookassa-webhook'),

    # Аутентификация
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/social/', include('social_django.urls', namespace='social')),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
]
