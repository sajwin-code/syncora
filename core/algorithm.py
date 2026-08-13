from django.utils import timezone
from django.db.models import Count
from .models import Post, User, PostView

def fetch_unseen_posts(user, max=500):
    viewed_posts = PostView.objects.filter(
        user=user
        ).order_by("created_at").values_list("post_id", flat=True)
    
    posts = Post.objects.exclude(id__in=viewed_posts).annotate(
        views_count=Count("views"),
        likes_count=Count("likes"),
        shares_count=Count("shares"),
        comments_count=Count("comments"),
    ).order_by("-created_at")[:max]

    return posts


def score_post(user, post):
    author = post.author
    age_hours = (timezone.now() - post.created_at).total_seconds() / 3600
    friend_score = 1

    if user.friends.filter(pk=author.pk).exists():
        friend_score = 10

    view_score = post.views_count * 1
    like_score = post.likes_count * 2
    comment_score = post.comments_count * 3
    share_score = post.shares_count * 5

    total_score = (view_score + like_score + comment_score + share_score - age_hours * 0.8) * friend_score

    return total_score


def get_posts(user, max=100):
    unseen_posts = fetch_unseen_posts(user)

    # scored_posts = [
    #     (score_post(user, post), post)
    #     for post in unseen_posts
    # ]

    # sorted_posts = sorted(
    #     scored_posts,
    #     key=lambda x: x[0]
    # )

    for post in unseen_posts:
        post.feed_score = score_post(user, post)

    sorted_posts = sorted(
        unseen_posts,
        key=lambda p: p.feed_score,
        reverse=True
    )

    return sorted_posts