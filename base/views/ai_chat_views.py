# base/views/ai_chat_views.py

import re
from functools import lru_cache

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q

from base.models import Product
from base.serializers import ProductSerializer

from pgvector.django import CosineDistance
from base.ai.embedding import embed_text


# ----------------------------
# Intent + Answer (Free)
# ----------------------------

def detect_intent(message: str) -> str:
    msg = (message or "").lower()
    if "compare" in msg or " vs " in msg or "vs" in msg:
        return "compare"
    if "under" in msg or "below" in msg or "budget" in msg:
        return "budget"
    if "best" in msg or "recommend" in msg:
        return "recommend"
    return "search"


def generate_answer(user_msg: str, products) -> str:
    if not products:
        return "I couldn’t find a close match. Tell me your budget + brand (optional)."

    intent = detect_intent(user_msg)

    top = products[0]
    top_price = top.discount_price if top.discountPercentage else top.price

    if intent == "compare" and len(products) >= 2:
        p1, p2 = products[0], products[1]
        p1_price = p1.discount_price if p1.discountPercentage else p1.price
        p2_price = p2.discount_price if p2.discountPercentage else p2.price
        return (
            f"Compare:\n"
            f"- {p1.name}: ৳{p1_price}, ⭐{p1.rating}, stock {p1.countInStock}\n"
            f"- {p2.name}: ৳{p2_price}, ⭐{p2.rating}, stock {p2.countInStock}\n"
            f"Tell me what matters most (price / performance / battery / brand)."
        )

    if intent == "budget":
        cheapest = min(
            [p for p in products if p.price is not None],
            key=lambda x: x.discount_price if x.discountPercentage else x.price,
            default=top,
        )
        c_price = cheapest.discount_price if cheapest.discountPercentage else cheapest.price
        return f"Best budget pick: **{cheapest.name}** (৳{c_price}). Also check the other options below."

    if intent == "recommend":
        # ✅ IMPORTANT: use re-ranked first item (not max rating)
        best = products[0]
        b_price = best.discount_price if best.discountPercentage else best.price
        return f"My top recommendation: **{best.name}** (⭐{best.rating}, ৳{b_price}). Here are more good matches."

    return f"I found {len(products)} good matches. Top match: **{top.name}** (৳{top_price})."


# ----------------------------
# Query normalization
# ----------------------------

STOP_WORDS = {
    "best", "top", "good", "recommend", "recommended", "show", "me", "please",
    "cheap", "cheapest", "buy", "need", "want", "under", "below", "within", "budget"
}

def normalize_query(q: str) -> str:
    q = (q or "").lower()
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    tokens = [t for t in q.split() if t and t not in STOP_WORDS]
    return " ".join(tokens).strip()


# ----------------------------
# Embedding cache (speed)
# ----------------------------

@lru_cache(maxsize=512)
def embed_query_cached(text: str):
    return embed_text(text)


# ----------------------------
# Retrieval (keyword + semantic)
# ----------------------------

def retrieve_products(q: str, top_k: int = 8):
    q_raw = (q or "").strip()
    if not q_raw:
        return []

    q_clean = normalize_query(q_raw)
    if not q_clean:
        q_clean = q_raw  # if user wrote only "best"

    keyword_qs = (
        Product.objects.select_related("category", "brand")
        .filter(
            Q(name__icontains=q_clean) |
            Q(brand__name__icontains=q_clean) |
            Q(category__name__icontains=q_clean) |
            Q(description__icontains=q_clean)
        )
        # rank “best” style queries toward high rating / reviews
        .order_by("-rating", "-numReviews", "-createdAt")[:top_k]
    )

    query_vec = embed_query_cached(q_clean)
    keyword_ids = keyword_qs.values_list("_id", flat=True)

    semantic_qs = (
        Product.objects.exclude(embedding__isnull=True)
        .exclude(_id__in=keyword_ids)
        .select_related("category", "brand")
        .annotate(distance=CosineDistance("embedding", query_vec))
        .filter(distance__lte=0.45)
        .order_by("distance")[:top_k]
    )

    final_list = list(keyword_qs) + list(semantic_qs)
    return final_list[:top_k]


# ----------------------------
# Domain re-ranking: Phones
# ----------------------------



PHONE_TERMS = {"phone", "mobile", "smartphone", "iphone", "android"}

def is_phone_query(text: str) -> bool:
    t = (text or "").lower()
    # detect real word "phone", not "headphones"
    return bool(re.search(r"\b(phone|mobile|smartphone|iphone|android)\b", t))


def phone_score(p: Product) -> int:
    name = (p.name or "").lower()
    desc = (p.description or "").lower()
    cat = (p.category.name if p.category else "").lower()

    score = 0

    # ✅ True phone signals (word boundaries)
    if re.search(r"\biphone\b", name):
        score += 12
    if re.search(r"\b(phone|mobile|smartphone)\b", name):
        score += 10

    if re.search(r"\biphone\b", desc):
        score += 6
    if re.search(r"\b(phone|mobile|smartphone)\b", desc):
        score += 4

    # ✅ Category boost (if you create Phones/Mobiles category later)
    if cat in {"phones", "mobiles"}:
        score += 8

    # ❌ Penalize accessories that contain "phone" as substring
    # (headphones, microphone, earphones etc.)
    if any(x in name for x in ["headphone", "headphones", "earphone", "earphones", "airpod", "airpods", "microphone"]):
        score -= 20
    if any(x in desc for x in ["headphone", "headphones", "earphone", "earphones", "airpod", "airpods", "microphone"]):
        score -= 10

    return score

# ----------------------------
# API endpoint
# ----------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_chat(request):
    msg = (request.data.get("message") or "").strip()
    if not msg:
        return Response({"detail": "message is required"}, status=status.HTTP_400_BAD_REQUEST)

    products = retrieve_products(msg, top_k=8)

    # ✅ Re-rank to ensure “best phone” chooses phone-like items first
    if is_phone_query(msg):
        products = sorted(
            products,
            key=lambda p: (phone_score(p), float(p.rating or 0), int(p.numReviews or 0)),
            reverse=True,
        )

    products_json = ProductSerializer(products, many=True).data
    answer = generate_answer(msg, products)

    return Response({
        "answer": answer,
        "intent": detect_intent(msg),
        "recommended_product_ids": [p["_id"] for p in products_json[:3]],
        "products": products_json
    })