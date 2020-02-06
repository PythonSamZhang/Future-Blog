from .. import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import flash, current_app, request
from flask_login import UserMixin, AnonymousUserMixin
from datetime import datetime
from markdown import markdown
import bleach
import hashlib
from flask_sqlalchemy import BaseQuery
from functools import reduce

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Admin': [Permission.FOLLOW, Permission.COMMENT,
                              Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN]
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()


    def __repr__(self):
        return '<Role %r>' % self.name

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True,default=datetime.utcnow())
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reciver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    read = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Chat %d>' % self.id

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol',
                        'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'p', 'br', 'hr']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, ['extra', 'codehilite', 'toc'], output_format='html'),
            tags=allowed_tags, strip=True))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    dark_theme = db.Column(db.Boolean, default=False)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id], 
                                backref=db.backref('follower', lazy='joined'), lazy='dynamic',
                                cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], 
                                backref=db.backref('followed', lazy='joined'), lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    chat_se = db.relationship('Chat', backref='author', lazy='dynamic', foreign_keys=[Chat.author_id])
    chat_re = db.relationship('Chat', backref='reciver', lazy='dynamic', foreign_keys=[Chat.reciver_id])
    unread = db.Column(db.Integer)
    likes = db.relationship('Like', backref='author', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='owner', lazy='dynamic')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role == None:
            if self.email == current_app.config['ADMIN']:
                self.role = Role.query.filter_by(name='Admin', default=False).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
        self.follow(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.ADMIN)


    def ping(self):
        self.last_seen = datetime.today()
        db.session.add(self)
        db.session.commit()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url, hash=hash, size=size, 
                                                                    default=default, rating=rating)

    def follow(self, user):
        if not self.is_following(user):
            f=Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()
    
    def is_following(self, user):
        try:
            if user.id is None:
                return False
        except:
            abort(404)
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        try:
            if user.id is None:
                return False
        except:
            abort(404)
        return self.followers.filter_by(follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)
   
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_admin(self):
        return False


login_manager.anonymous_user = AnonymousUser

def keywords_split(keywords):
    return keywords.replace(u',', ' ') \
        .replace(u';', ' ') \
        .replace(u'+', ' ') \
        .replace(u'；', ' ') \
        .replace(u'，', ' ') \
        .replace(u'　', ' ') \
        .split(' ')

class PostQuery(BaseQuery):
    
    def public(self):
        return self

    def search(self, keyword):
        criteria = []

        for keyword in keywords_split(keyword):
            keyword = u'%{0}%'.format(keyword)
            criteria.append(db.or_(Post.title.ilike(keyword), ))

        q = reduce(db.or_, criteria)
        return self.public().filter(q)

class Post(db.Model):
    __tablename__ = 'posts'
    query_class = PostQuery
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    title = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    favorites = db.relationship('Favorite', backref='post', lazy='dynamic')
    read_by = db.Column(db.Integer, default=0)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol',
                        'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'p', 'br', 'hr', 'img']
        attrs = {
                    '*': ['class'],
                    'a': ['href', 'rel'],
                    'img': ['src', 'alt'],
                }
        target.body_html = bleach.linkify(bleach.clean(markdown(value, output_format='html'),
                                            tags=allowed_tags, attributes=attrs, strip=True))

db.event.listen(Post.body, 'set', Post.on_changed_body)


class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    version = db.Column(db.String(64))

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    posts = db.relationship('Post', backref='categories', lazy='dynamic')

    @staticmethod
    def default_categories():
        names = ['IT', '新闻', '体育', '美食', '旅行', '科技']
        for name in names:
            try:
                c = Category(name=name)
                db.session.add(c)
                db.session.commit()
            except:
               print('error')

    def __repr__(self):
        return '<Category %s>' % self.name

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))

class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16