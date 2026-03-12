from collections import Counter
from db import get_connection

KEYWORDS = [
    "정사이즈", "큼", "작음", "오버핏", "세미오버핏", "정핏", "슬림핏",
    "기장", "어깨", "편함", "여유", "타이트", "만족", "무난"
]


def extract_keywords(texts):
    counts = Counter()
    for text in texts:
        if not text:
            continue
        for keyword in KEYWORDS:
            if keyword in text:
                counts[keyword] += 1
    return dict(counts.most_common(5))


def get_size_recommendation(current_user_id, product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, gender, height, weight, preferred_fit, usual_size
                FROM users
                WHERE user_id = %s
                """,
                (current_user_id,),
            )
            current_user = cursor.fetchone()

            if not current_user:
                return {
                    "recommended_size": None,
                    "similar_user_count": 0,
                    "message": "사용자 정보를 찾을 수 없습니다.",
                }

            if not current_user.get("height") or not current_user.get("weight") or not current_user.get("preferred_fit"):
                return {
                    "recommended_size": None,
                    "similar_user_count": 0,
                    "message": "마이페이지에서 키/몸무게/선호 핏 정보를 먼저 입력해 주세요.",
                }

            cursor.execute(
                """
                SELECT
                    r.review_id,
                    r.purchased_size,
                    r.size_feel,
                    r.fit_feel,
                    r.rating,
                    r.review_text,
                    u.user_id,
                    u.height,
                    u.weight,
                    u.gender,
                    u.preferred_fit,
                    u.usual_size
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.product_id = %s
                AND u.user_id <> %s
                AND (%s IS NULL OR u.gender = %s)
                AND ABS(u.height - %s) <= 3
                AND ABS(u.weight - %s) <= 5
                AND u.preferred_fit = %s
                """,
                (
                    product_id,
                    current_user_id,
                    current_user.get("gender"),
                    current_user.get("gender"),
                    current_user["height"],
                    current_user["weight"],
                    current_user["preferred_fit"],
                ),
            )
            similar_reviews = cursor.fetchall()

            if not similar_reviews:
                return {
                    "recommended_size": None,
                    "similar_user_count": 0,
                    "message": "아직 비슷한 체형과 선호 핏 데이터를 가진 리뷰가 부족합니다.",
                }

            size_counts = Counter(r["purchased_size"] for r in similar_reviews if r.get("purchased_size"))
            size_feel_counts = Counter(r["size_feel"] for r in similar_reviews if r.get("size_feel"))
            fit_feel_counts = Counter(r["fit_feel"] for r in similar_reviews if r.get("fit_feel"))
            avg_rating = round(sum(r["rating"] for r in similar_reviews if r.get("rating")) / len(similar_reviews), 2)
            recommended_size, recommended_size_count = size_counts.most_common(1)[0]
            keyword_counts = extract_keywords([r.get("review_text", "") for r in similar_reviews])

            positive = []
            if size_feel_counts:
                positive.append(f"사이즈 체감은 '{size_feel_counts.most_common(1)[0][0]}' 의견이 가장 많습니다")
            if fit_feel_counts:
                positive.append(f"핏 체감은 '{fit_feel_counts.most_common(1)[0][0]}' 평가가 많습니다")

            summary = (
                f"비슷한 체형 사용자 {len(similar_reviews)}명 중 {recommended_size} 사이즈를 가장 많이 선택했고, "
                f"평균 만족도는 {avg_rating}점입니다. " + ", ".join(positive) + "."
            )

            return {
                "recommended_size": recommended_size,
                "recommended_size_count": recommended_size_count,
                "similar_user_count": len(similar_reviews),
                "average_rating": avg_rating,
                "size_distribution": dict(size_counts),
                "size_feel_distribution": dict(size_feel_counts),
                "fit_feel_distribution": dict(fit_feel_counts),
                "keyword_distribution": keyword_counts,
                "message": "유사 체형 + 유사 선호 핏 기반 추천 결과입니다.",
                "summary": summary,
                "user_basis": {
                    "height": current_user["height"],
                    "weight": current_user["weight"],
                    "preferred_fit": current_user["preferred_fit"],
                    "usual_size": current_user.get("usual_size"),
                },
            }
    finally:
        conn.close()
