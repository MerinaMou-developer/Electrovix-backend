from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from base.models import Product, Review
from base.serializers import ProductSerializer

from rest_framework import status
from django.db.models import F,Q
from base.models import Category,Brand
from base.serializers import CategorySerializer,BrandSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def getProducts(request):
    query = request.query_params.get('keyword', '')
    category_slug = request.query_params.get('category_slug', '')
    brand_slug = request.query_params.get('brand_slug', '')
    filter_by = request.query_params.get('filter_by')
    min_price = request.query_params.get('minPrice', '')
    max_price = request.query_params.get('maxPrice', '')

    query_filter = Q(name__icontains=query)

    # Filter by category
    if category_slug:
        query_filter &= Q(category__slug=category_slug)
    
    # Filter by brand
    if brand_slug:
        query_filter &= Q(brand__slug=brand_slug)
    
    # Filter by price range
    if min_price:
        try:
            query_filter &= Q(price__gte=float(min_price))
        except ValueError:
            return Response({'detail': 'Invalid minPrice value'}, status=status.HTTP_400_BAD_REQUEST)
    if max_price:
        try:
            query_filter &= Q(price__lte=float(max_price))
        except ValueError:
            return Response({'detail': 'Invalid maxPrice value'}, status=status.HTTP_400_BAD_REQUEST)

    # Handle 'filter_by' conditions
    if filter_by == 'best_seller':
        products = Product.objects.filter(query_filter).select_related('category', 'brand').order_by('-numReviews')
    elif filter_by == 'featured':
        products = Product.objects.filter(query_filter, rating__gte=4.0).select_related('category', 'brand').order_by('-rating')
    elif filter_by == 'latest':
        products = Product.objects.filter(query_filter).select_related('category', 'brand').order_by('-createdAt')
    elif filter_by == 'most_reviewed':
        products = Product.objects.filter(query_filter).select_related('category', 'brand').order_by('-numReviews')
    elif filter_by == 'discount':
        # Fetch all products and filter them in Python
        all_products = Product.objects.filter(query_filter).select_related('category', 'brand')
        products = [
            product for product in all_products
            if product.discountPercentage and product.price and product.discount_price < product.price
        ]
    else:
        products = Product.objects.filter(query_filter).select_related('category', 'brand').order_by('-createdAt')


    # Paginate the results
    page = request.query_params.get('page', 1)
    paginator = Paginator(products, 8)

    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Serialize and return the data
    serializer = ProductSerializer(products, many=True)

    return Response({
        'products': serializer.data,
        'page': int(page),
        'pages': paginator.num_pages,
        'total': paginator.count,
    })

@api_view(['GET'])
def getCategories(request):
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getBrand(request):
    brand = Brand.objects.all()
    serializer = BrandSerializer(brand, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def getTopProducts(request):
    products = Product.objects.filter(rating__gte=4).order_by('-rating')[0:5]
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def getProduct(request,pk):

    product= Product.objects.get(_id=pk)
    serializer=ProductSerializer(product,many=False)

    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAdminUser])
def createProduct(request):
    user = request.user
    category = Category.objects.first()  # Assign a default category or handle appropriately
    brand = Brand.objects.first()

    if not category:
        return Response({'detail': 'No category found. Please add a category first.'}, status=400)
    if not brand:
        return Response({'detail': 'No brand name found. Please add a brand first.'}, status=400)

    discount_percentage = request.data.get('discountPercentage', 0.00)  # Default to 0.00 if not provided

    product = Product.objects.create(
        user=user,
        name='Sample Product',
        price=0.00,
        brand=brand,
        countInStock=0,
        category=category,  # Assign a valid Category instance
        description='',
        discountPercentage=discount_percentage  # Set the discount percentage
    )

    serializer = ProductSerializer(product, many=False)
    return Response(serializer.data)



from django.shortcuts import get_object_or_404
from base.models import Product, Category
from base.serializers import ProductSerializer

@api_view(['PUT'])
@permission_classes([IsAdminUser])
def updateProduct(request, pk):
    data = request.data

    if not data.get('category') or not data.get('brand'):
        return Response(
            {'detail': 'Category and Brand are required and must be valid.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        product = Product.objects.get(_id=pk)
        product.name = data['name']
        product.price = data['price']
        product.discountPercentage = data.get('discountPercentage', product.discountPercentage)  # Update discount

        # Use slug to find the category
        category_slug = data['category']
        brand_slug = data['brand']

        try:
            product.category = Category.objects.get(slug=category_slug)
        except Category.DoesNotExist:
            return Response(
                {'detail': f'Invalid category slug: {category_slug}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product.brand = Brand.objects.get(slug=brand_slug)
        except Brand.DoesNotExist:
            return Response(
                {'detail': f'Invalid brand slug: {brand_slug}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product.countInStock = data['countInStock']
        product.description = data['description']
        product.save()

        serializer = ProductSerializer(product, many=False)
        return Response(serializer.data)

    except Product.DoesNotExist:
        return Response(
            {'detail': f'Product with ID {pk} does not exist.'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)



@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def deleteProduct(request, pk):
    product = Product.objects.get(_id=pk)
    product.delete()
    return Response('Producted Deleted')

@api_view(['POST'])
def uploadImage(request):
    data = request.data

    product_id = data['product_id']
    product = Product.objects.get(_id=product_id)

    product.image = request.FILES.get('image')
    product.save()

    return Response('Image was uploaded')





@api_view(['POST'])
@permission_classes([IsAuthenticated])
def createProductReview(request, pk):
    user = request.user
    product = Product.objects.get(_id=pk)
    data = request.data

    # 1 - Review already exists
    alreadyExists = product.review_set.filter(user=user).exists()
    if alreadyExists:
        content = {'detail': 'Product already reviewed'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    # 2 - No Rating or 0
    elif data['rating'] == 0:
        content = {'detail': 'Please select a rating'}
        return Response(content, status=status.HTTP_400_BAD_REQUEST)

    # 3 - Create review
    else:
        review = Review.objects.create(
            user=user,
            product=product,
            name=user.first_name,
            rating=data['rating'],
            comment=data['comment'],
        )

        reviews = product.review_set.all()
        product.numReviews = len(reviews)

        total = 0
        for i in reviews:
            total += i.rating

        product.rating = total / len(reviews)
        product.save()

        return Response('Review Added')

