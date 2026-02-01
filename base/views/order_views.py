from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from base.models import Product, Order, OrderItem, ShippingAddress
from base.serializers import ProductSerializer, OrderSerializer

from rest_framework import status
from datetime import datetime
from sslcommerz_lib import SSLCOMMERZ
from django.conf import settings
from decouple import config
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def addOrderItems(request):
    user = request.user
    data = request.data

    # Ensure all required fields are present
    required_fields = ['paymentMethod', 'taxPrice', 'shippingPrice', 'totalPrice', 'orderItems', 'shippingAddress']
    for field in required_fields:
        if field not in data:
            return Response({'detail': f'Missing field: {field}'}, status=status.HTTP_400_BAD_REQUEST)

    orderItems = data['orderItems']

    if not orderItems or len(orderItems) == 0:
        return Response({'detail': 'No Order Items'}, status=status.HTTP_400_BAD_REQUEST)

    # Create order
    order = Order.objects.create(
        user=user,
        paymentMethod=data['paymentMethod'],
        taxPrice=data['taxPrice'],
        shippingPrice=data['shippingPrice'],
        totalPrice=data['totalPrice']
    )

    # Create shipping address
    ShippingAddress.objects.create(
        order=order,
        address=data['shippingAddress']['address'],
        city=data['shippingAddress']['city'],
        postalCode=data['shippingAddress']['postalCode'],
        country=data['shippingAddress']['country'],
        phone=data['shippingAddress']['phone']
    )

    # Create order items and set order relationship
    for i in orderItems:
        try:
            product = Product.objects.get(_id=i['product'])
        except Product.DoesNotExist:
            return Response({'detail': f'Product with id {i["product"]} does not exist'}, status=status.HTTP_404_NOT_FOUND)

        item = OrderItem.objects.create(
            product=product,
            order=order,
            name=product.name,
            qty=i['qty'],
            price=i['price'],
            image=product.image.url,
        )

        # Update stock
        if product.countInStock >= item.qty:
            product.countInStock -= item.qty
            product.save()
        else:
            return Response({'detail': f'Not enough stock for product {product.name}'}, status=status.HTTP_400_BAD_REQUEST)

    # Serialize and return order details
    serializer = OrderSerializer(order, many=False)
    return Response(serializer.data)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiatePayment(request):
    data = request.data
    user = request.user

    # Validate request payload
    if 'order_id' not in data:
        return Response({'detail': 'Missing order_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Use `_id` instead of `id`
        order = Order.objects.get(_id=data['order_id'], user=user)
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

    # SSLCommerz initialization and response logic
    settings = {
        'store_id': config('STORE_ID'),
        'store_pass': config('STORE_PASS'),
        'issandbox': config('ISSANDBOX', cast=bool),
    }


    sslcz = SSLCOMMERZ(settings)

    post_body = {
        'total_amount': order.totalPrice,
        'currency': 'BDT',
        'tran_id': f'order_{order._id}',
        'success_url': config('SUCCESS_URL'),
        'fail_url': config('FAIL_URL'),
        'cancel_url': config('CANCEL_URL'),
        'emi_option': 0,
        'cus_name': user.first_name + ' ' + user.last_name,
        'cus_email': user.email,
        'cus_phone': order.shippingaddress.phone,
        'cus_add1': order.shippingaddress.address,
        'cus_city': order.shippingaddress.city,
        'cus_postcode': order.shippingaddress.postalCode,
        'cus_country': order.shippingaddress.country,
        'shipping_method': 'NO',
        'multi_card_name': '',
        # Use `orderitem_set` to access related items
        'num_of_item': order.orderitem_set.count(),
        'product_name': ', '.join([item.name for item in order.orderitem_set.all()]),
        'product_category': 'General',
        'product_profile': 'general',
    }

    response = sslcz.createSession(post_body)

    if 'GatewayPageURL' in response:
        order.transaction_id = post_body['tran_id']
        order.save()
        return Response({'GatewayPageURL': response['GatewayPageURL']})
    else:
        return Response({'detail': 'Failed to initiate payment'}, status=status.HTTP_400_BAD_REQUEST)


from django.shortcuts import redirect

@csrf_exempt
@api_view(['POST'])
def paymentSuccess(request):
    print("Authorization Header:", request.headers.get("Authorization"))
    data = request.data
    try:
        order = Order.objects.get(transaction_id=data['tran_id'])
        if data['status'] == 'VALID':
            order.isPaid = True
            order.paidAt = datetime.now()
            order.save()
            # Redirect to frontend confirmation page
            return redirect(f"https://electrovix.netlify.app/order/{order._id}?status=success")
        else:
            return redirect(f"https://electrovix.netlify.app/order/{order._id}?status=fail")
    except Order.DoesNotExist:
        return Response({'detail': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def paymentFail(request):
    data = request.data
    transaction_id = data.get('tran_id', 'N/A')
    print(f"Payment failed for transaction ID: {transaction_id}")
    return redirect(f"https://electrovix.netlify.app/order/0?status=fail")

@api_view(['POST'])
def paymentCancel(request):
    data = request.data
    transaction_id = data.get('tran_id', 'N/A')
    print(f"Payment canceled for transaction ID: {transaction_id}")
    return redirect(f"https://electrovix.netlify.app/order/0?status=cancel")




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getMyOrders(request):
    user = request.user
    orders = user.order_set.all()

    # Pagination logic
    page = request.query_params.get('page', 1)
    paginator = Paginator(orders, 10)  # Show 10 orders per page

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    serializer = OrderSerializer(orders, many=True)
    return Response({
        'orders': serializer.data,
        'page': int(page),
        'pages': paginator.num_pages,
        'total': paginator.count,
    })



@api_view(['GET'])
@permission_classes([IsAdminUser])
def getOrders(request):
    orders = Order.objects.all()

    # Pagination logic
    page = request.query_params.get('page', 1)
    paginator = Paginator(orders, 10)  # Show 10 orders per page

    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    serializer = OrderSerializer(orders, many=True)
    return Response({
        'orders': serializer.data,
        'page': int(page),
        'pages': paginator.num_pages,
        'total': paginator.count,
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def getOrderById(request, pk):

    user = request.user

    try:
        order = Order.objects.get(_id=pk)
        if user.is_staff or order.user == user:
            serializer = OrderSerializer(order, many=False)
            return Response(serializer.data)
        else:
            Response({'detail': 'Not authorized to view this order'},
                     status=status.HTTP_400_BAD_REQUEST)
    except:
        return Response({'detail': 'Order does not exist'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def updateOrderToPaid(request, pk):
    order = Order.objects.get(_id=pk)

    order.isPaid = True
    order.paidAt = datetime.now()
    order.save()

    return Response('Order was paid')


@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateOrderToDelivered(request, pk):
    order = Order.objects.get(_id=pk)

    order.isDelivered = True
    order.deliveredAt = datetime.now()
    order.save()

    return Response('Order was delivered')
