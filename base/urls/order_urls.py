from django.urls import path
from base.views import order_views as views

urlpatterns = [
    path('', views.getOrders, name='orders'),  # Get all orders
    path('add/', views.addOrderItems, name='orders-add'),  # Add order items
    path('initiate-payment/', views.initiatePayment, name='initiate-payment'),  # Initiate payment
    path('payment-success/', views.paymentSuccess, name='payment-success'),  # Handle payment success
    path('payment-fail/', views.paymentFail, name='payment-fail'),  # Handle payment failure
    path('payment-cancel/', views.paymentCancel, name='payment-cancel'),  # Handle payment cancellation
    path('myorders/', views.getMyOrders, name='myorders'),  # Get current user's orders
    path('<str:pk>/deliver/', views.updateOrderToDelivered, name='order-delivered'),  # Mark order as delivered
    path('<str:pk>/', views.getOrderById, name='user-order'),  # Get order by ID
    path('<str:pk>/pay/', views.updateOrderToPaid, name='pay'),  # Update order as paid
]
