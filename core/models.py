from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
import string

# Create your models here.

#Functions
def validate_username(value):
    if not 7 <= len(value) <= 15:
        raise ValidationError(
            "Username must be between 7 and 15 characters."
        )

    allowed = set(string.ascii_letters + string.digits + "_.-")

    invalid = sorted(set(value) - allowed)

    if invalid:
        raise ValidationError(
            f"Character(s): {', '.join(invalid)} are not allowed."
        )

    
class User(AbstractUser):

    profile_pic = models.ImageField("Profile Picture", blank=True, null=True, upload_to="profile_pic/")
    friends = models.ManyToManyField("self", symmetrical=True, blank=True,)
    private_account = models.BooleanField(default=False)




    def clean(self):
        super().clean()
        validate_username(self.username)


# Managers

class FriendRequestManager(models.Manager):
    @transaction.atomic
    def create_request(self, sender, receiver):
        if sender == receiver:
                raise ValidationError(
                    "You cannot send a friend request to yourself."
                )

        if Block.objects.filter(
            blocker=receiver,
            blocked=sender,
        ).exists():
            raise ValidationError(
                "You cannot send a friend request to this user."
            )

        if Block.objects.filter(
            blocker=sender,
            blocked=receiver,
        ).exists():
            raise ValidationError(
                "Unblock this user to add them to your friends."
            )
        
        if sender.friends.filter(pk=receiver.pk).exists():
            raise ValidationError(
                "You are already friends with this user."
            )

        reverse_request = self.filter(
            sender=receiver,
            receiver=sender,
        ).first()

        if reverse_request:
            sender.friends.add(receiver)
            reverse_request.delete()
            return None
        
        existing = self.filter(
            sender=sender,
            receiver=receiver,
        ).first()

        if existing:
            raise ValidationError(
                "Friend request already exists."
            )


        return self.create(
            sender=sender,
            receiver=receiver,
        )

    @transaction.atomic
    def accept_request(self, sender, receiver):
        request = self.filter(sender=sender, receiver=receiver).first()

        if sender.friends.filter(pk=receiver.pk).exists():
            raise ValidationError(f"{sender.username} is already friends with {receiver.username}")

        if not request:
            raise ValidationError(
                "Friend request does not exist."
            )

        
        if Block.objects.filter(
            blocker=receiver,
            blocked=sender,
        ).exists():
            raise ValidationError(
                "You cannot send a friend request to this user."
            )

        if Block.objects.filter(
            blocker=sender,
            blocked=receiver,
        ).exists():
            raise ValidationError(
                "Unblock this user to add them to your friends."
            )
        

        sender.friends.add(receiver)
        request.delete()

        return True

    def reject_request(self, sender, receiver):
        deleted, _ = self.filter(
            sender=sender,
            receiver=receiver,
        ).delete()

        if not deleted:
            raise ValidationError(
                "Friend request does not exist."
            )


    def cancel_request(self, sender, receiver):
        deleted, _ = self.filter(
            sender=sender,
            receiver=receiver,
        ).delete()

        if not deleted:
            raise ValidationError(
                "Friend request does not exist."
            )



class BlockManager(models.Manager):

    @transaction.atomic
    def block_user(self, blocker, blocked):

        if blocker == blocked:
            raise ValidationError(
                "You cannot block yourself."
            )

        # Remove friendship
        blocker.friends.remove(blocked)

        # Remove pending requests in either direction
        FriendRequest.objects.filter(
            sender=blocker,
            receiver=blocked,
        ).delete()

        FriendRequest.objects.filter(
            sender=blocked,
            receiver=blocker,
        ).delete()

        # Create the block
        return self.create(
            blocker=blocker,
            blocked=blocked,
        )

        

class FriendRequest(models.Model):
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )

    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )

    objects = FriendRequestManager()


    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                name="unique_friend_request",
            ),
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("receiver")),
                name="cannot_friend_request_self",
            ),
        ]





class Post(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="posts",
    )

    content = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def get_like_count(self):
        return self.likes.count()

    def get_comment_count(self):
        return self.comments.count()

    def get_share_count(self):
        return self.shares.count()



class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(
        upload_to="post_images/",
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ["order"]


class PostView(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="views",
    )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="views",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_user_post_view",
            ),
        ]


class Like(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="likes",
        )
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
        )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_user_post_like",
            ),
        ]




class Comment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="comments",
        )
    
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        )
    
    content = models.TextField(blank=False, max_length=500)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


class Share(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="shares",
    )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="shares",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "post"],
                name="unique_user_post_share",
            ),
        ]


class Notification(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name="notifications"
        )
    
    content = models.TextField(max_length=100)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

class Block(models.Model):
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_users",
    )

    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    objects = BlockManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"],
                name="unique_block",
            ),
            models.CheckConstraint(
                condition=~models.Q(
                    blocker=models.F("blocked")
                ),
                name="cannot_block_self",
            ),
        ]
