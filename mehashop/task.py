from celery import shared_task

@shared_task
def send_order_notification(order_id):
    # Логика отправки уведомления
    print(f"Заказ {order_id} создан")