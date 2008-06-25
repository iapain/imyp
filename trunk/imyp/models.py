from google.appengine.ext import db
from django import newforms as forms

### GQL query cache ###


_query_cache = {}

def gql(cls, clause, *args, **kwds):
    """Return a query object, from the cache if possible.
    Args:
        cls: a db.Model subclass.
        clause: a query clause, e.g. 'WHERE draft = TRUE'.
        *args, **kwds: positional and keyword arguments to be bound to the query.

    Returns:
      A db.GqlQuery instance corresponding to the query with *args and
      **kwds bound to the query.
    """
    query_string = 'SELECT * FROM %s %s' % (cls.kind(), clause)
    query = _query_cache.get(query_string)
    if query is None:
        _query_cache[query_string] = query = db.GqlQuery(query_string)
    query.bind(*args, **kwds)
    return query

class Item(db.Model):
    title = db.StringProperty(required=True)
    tab_title = db.StringProperty(required=True)
    verbose_title = db.StringProperty(required=True)
    created_on = db.DateTimeProperty(auto_now_add = True)
    
class UserFeed(db.Model):
    type = db.ReferenceProperty(Item)
    user = db.UserProperty(required=True)
    feed_url = db.StringProperty(required=True)
    created_on = db.DateTimeProperty(auto_now_add = True)
    
class IconItem(db.Model):
    icon_src = db.BlobProperty(default=None)
    

class Account(db.Model):
    user = db.UserProperty(required=True)
    email = db.EmailProperty(required=True)  # key == <email>
    nickname = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def get_account_for_user(cls, user):
        """Get the Account for a user, creating a default one if needed."""
        email = user.email()
        assert email
        key = '<%s>' % email
        nickname = user.nickname()
        if '@' in nickname:
            nickname = nickname.split('@', 1)[0]
        assert nickname
        return cls.get_or_insert(key, user=user, email=email, nickname=nickname)
    
    @classmethod
    def get_account_for_email(cls, email):
        """Get the Account for an email address, or return None."""
        assert email
        key = '<%s>' % email
        return cls.get_by_key_name(key)



    
class UserItem(db.Model):
    type = db.ReferenceProperty(Item)
    user = db.UserProperty(required=True)
    title = db.StringProperty(required=True)
    link = db.StringProperty(required=True)
    media_src = db.TextProperty()
    author = db.StringProperty()
    #desc = db.StringProperty()
    icon = db.ReferenceProperty(IconItem)
    is_featured = db.BooleanProperty()
    item_date = db.DateTimeProperty()
    created_on = db.DateTimeProperty(auto_now_add = True)
    
    @classmethod
    def get_absolute_url(self):
        return '/%s/%s/' % (self.type.title(), self.key())
    
    @classmethod
    def get_icon_url(self):
        return '/icon/%s/' % self.key_name()
    
    def __str__(self):
        return self.title
    
    def get_by_type(self, type, limit=None):
        records = gql(UserItem, "WHERE type = :type", type.key())
        if limit is None:
            return records
        else:
            return records[:limit]
