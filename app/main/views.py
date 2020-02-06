from flask import render_template, url_for, request, redirect, flash, abort, make_response
from flask_login import login_user, logout_user, login_required, current_user
from .models import *
from .forms import *
from . import main
from app.decorators import *

@main.route('/')
def index():
    categories = Category.query.all()
    chats = Chat.query.all()
    unread = []
    posts = Post.query.order_by(Post.read_by.desc()).all()
    posts = posts[:5]
    u = current_user._get_current_object()
    for chat in chats:
        if chat.reciver == u:
            unread.append(chat)
    return render_template('index.html', categories=categories, unread=unread, posts=posts)

@main.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            next = request.args.get('next')
            if next is None or next[:1]!='/':
                next = url_for('main.index')
            return redirect(next)
        flash('用户名或密码错误')
    return render_template('login.html', form=form)

@main.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('你现在已登出')
    return redirect(url_for('main.index'))

@main.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data,
                    unread=0)
        db.session.add(user)
        db.session.commit()
        login_user(user, True)
        return redirect(url_for('main.index'))
    return render_template('register.html', form=form)

@main.route('/user/<username>/')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)

@main.route('/news/')
def news():
    page = request.args.get('page', 1, type=int)
    pagination = News.query.order_by(News.timestamp.desc()).paginate(
        page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False
    )
    newsall = pagination.items
    return render_template('news.html', newsall=newsall, pagination=pagination)

@main.route('/edit-profile/', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('你的个人资料已更新')
        return redirect(url_for('main.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>/', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('个人资料已更新')
        return redirect(url_for('main.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route('/blog/', methods=['GET', 'POST'])
def blog(categories=None, id=None):
    form = PostForm()
    form2 = UploadForm()
    categories = request.args.get("categories")
    id = request.args.get("id")
    if not current_user.is_authenticated:
        flash('注意：你需要登录才能开始写博客！')
    if current_user.is_authenticated and form.validate_on_submit():
        title = form.title.data
        if id != None:
            category = categories
            post = Post(body=form.body.data, title=form.title.data, author=current_user._get_current_object(), category_id=int(id), read_by=0)
        else:
            post = Post(body=form.body.data, title=form.title.data, author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('main.blog'))
    if current_user.can(Permission.WRITE) and form2.validate_on_submit():
        time = current_user.username + str(datetime.now().year) + str(datetime.now().month) + str(datetime.now().day) + str(datetime.now().second)
        name = hashlib.md5(time.encode('UTF-8')).hexdigest()[:20]
        filename = photos.save(form2.photo.data, name=name+'.')
        file = photos.url(filename)
        flash('图片已上传。请复制'+'<img src="'+file+'"/>'+'到图片的位置')
    else:
        file = None
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False
    )
    posts = pagination.items
    return render_template('blog.html', form=form, form2=form2, posts=posts, show_followed=show_followed, pagination=pagination, category=categories)

@main.route('/blog/upload/', methods=['GET', 'POST'])
@login_required
def upload():
    form = UploadForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        time = str(datetime.now().year) + str(datetime.now().month) + str(datetime.now().day) + str(datetime.now().second)
        name = hashlib.md5(time.encode('UTF-8')).hexdigest()[:20]
        filename = photos.save(form.photo.data, name=name+'.')
        file = photos.url(filename)
        flash('图片已上传。请复制<code>'+'<img src="'+file+'"/>'+'</code>到图片的位置')
    else:
        file = None
        flash('图片上传时错误')

@main.route('/blog/post/<int:id>/', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    post.read_by += 1
    db.session.add(post)
    db.session.commit()
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('你的评论已发布')
        return redirect(url_for('main.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)

@main.route('/blog/edit/<int:id>/', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        post.title = form.title.data
        db.session.add(post)
        db.session.commit()
        flash('博客已更新')
        return redirect(url_for('main.post', id=post.id))
    form.body.data = post.body
    form.title.data = post.title
    return render_template('edit_post.html', form=form)

@main.route('/follow/<username>/')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('main.index'))
    if current_user.is_following(user):
        flash('你已经关注着此用户了')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    flash('你现在在关注着%s.' % username)
    return redirect(url_for('main.user', username=username))


@main.route('/unfollow/<username>/')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('用户不存在')
        return redirect(url_for('main.index'))
    if not current_user.is_following(user):
        flash('你没有关注此用户')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    flash('你没有再关注着%s.' % username)
    return redirect(url_for('main.user', username=username))


@main.route('/followers/<username>/')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('无效的用户')
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)

@main.route('/all/')
@login_required
def show_all():
    resp = make_response(redirect(url_for('main.blog')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp

@main.route('/followed/')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('main.blog')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp

@main.route('/admin/comments/')
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('admin/admin_moderate.html', comments=comments,
                           pagination=pagination, page=page, Comment=Comment)


@main.route('/blog/moderate/enable/<int:id>/')
@login_required
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/blog/moderate/disable/<int:id>/')
@login_required
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('main.moderate',
                            page=request.args.get('page', 1, type=int)))

@main.route('/admin/')
@permission_required(Permission.ADMIN)
def admin():
    return render_template('admin/admin.html', User=User, Post=Post, Comment=Comment)

@main.route('/admin/users/')
@permission_required(Permission.ADMIN)
def admin_users():
    users = User.query.all()
    query = User.query
    return render_template('admin/admin_users.html', users=users, query=query)

@main.route('/admin/users/edit-roles/<int:id>/', methods=['GET', 'POST'])
@admin_required
def admin_edit_roles(id):
    user = User.query.get_or_404(id)
    form = AdminEditRoleForm(user=user)
    if form.validate_on_submit():
        user.role = Role.query.get(form.role.data)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('main.admin_users', users=User.query.all()))
    form.role.data = user.role_id
    return render_template('admin/admin_users_role.html', form=form, last_page='/admin/users/')

@main.route('/admin/users/posts/<int:id>/')
@admin_required
def admin_user_posts(id):
    user = User.query.get_or_404(id)
    posts = Post.query.filter_by(author_id=id).all()
    return render_template('/admin/admin_user_posts.html', user=user, posts=posts, 
                            last_page='/admin/users/posts/'+str(id)+'/')

@main.route('/admin/posts/')
@admin_required
def admin_posts():
    posts = Post.query.all()
    count = Post.query.count()
    return render_template('/admin/admin_posts.html', posts=posts, count=count)

@main.route('/admin/users/post/<int:id>/')
@admin_required
def admin_post_view(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('admin/admin_post_view.html', posts=[post], 
                           comments=comments, pagination=pagination, last_page='/admin/users/posts/'+str(post.author_id))

@main.route('/admin/users/post/edit/<int:id>/', methods=['GET', 'POST'])
@admin_required
def admin_edit(id):
    post = Post.query.get_or_404(id)
    if not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        post.title = form.title.data
        db.session.add(post)
        db.session.commit()
        flash('博客已更新')
        return redirect(url_for('main.admin_post_view', id=post.id))
    form.body.data = post.body
    form.title.data = post.title
    return render_template('admin/admin_edit_post.html', form=form)

@main.route('/admin/users/remove_con/<int:id>/', methods=['GET', 'POST'])
@admin_required
def remove_con(id):
    form = AdminConfirmRemoveForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            return redirect(url_for('main.remove_user', id=id))
        else:
            flash('错误的密码')
    return render_template('admin/admin_confirm_remove.html', form=form, last_page='/admin/users/')

@main.route('/admin/users/remove/<int:id>/', methods=['GET', 'POST'])
@admin_required
def remove_user(id):
    user = User.query.get_or_404(id)
    posts = Post.query.filter_by(author_id=id).all()
    comments = Comment.query.filter_by(author_id=id).all()
    for post in posts:
        db.session.delete(post)
    for comment in comments:
        db.session.delete(comment)
    db.session.delete(user)
    db.session.commit()
    flash('用户%s已被移除' % user.username)
    return redirect(url_for('main.admin_users'))

@main.route('/admin/log/')
@admin_required
def log():
    return render_template('/admin/log.html')

@main.route('/admin/news/edit/', methods=['GET', 'POST'])
@admin_required
def edit_news():
    form = NewsForm()
    if form.validate_on_submit():
        news = News(title=form.title.data, body=form.body.data, version=form.version.data)
        db.session.add(news)
        db.session.commit()
        flash('新闻已发布')
        return redirect(url_for('.admin_news'))
    return render_template('/admin/admin_add_news.html', form=form)

@main.route('/admin/news/')
@admin_required
def admin_news():
    query = News.query
    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(News.timestamp.desc()).paginate(
        page, per_page=current_app.config['POSTS_PER_PAGE'], error_out=False
    )
    news = pagination.items
    return render_template('/admin/admin_news.html', News=News, newsall=news, pagination=pagination)

@main.route('/blog/category/')
@login_required
def choose_category():
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@main.route('/blog/categories/add/<int:id>/')
@login_required
def add_category(id):
    category = Category.query.get_or_404(id)
    return redirect(url_for('main.blog', categories=category.name, id=id))

@main.route('/blog/categories/new/', methods=['GET', 'POST'])
@login_required
def new_category():
    form = CategoryForm()
    if form.validate_on_submit():
        c = Category(name=form.name.data)
        db.session.add(c)
        db.session.commit()
        return redirect(url_for('main.add_category', id=c.id))
    return render_template('new_category.html', form=form)

@main.route('/category/<int:id>/')
def view_category(id):
    category = Category.query.get_or_404(id)
    posts = Post.query.all()
    return render_template('category_posts.html', category=category, posts=posts)

@main.route('/chat/<username>/', methods=['GET', 'POST'])
@login_required
def chat(username):
    reciver = User.query.filter_by(username=username).first()
    author = current_user._get_current_object()
    if not current_user.is_following(reciver) and not reciver.is_following(current_user):
        flash('你需要先关注%s！' % reciver.username)
    else:
        form = ChatForm()
        chats = Chat.query.all()
        author.unread = 0
        db.session.add(author)
        db.session.commit()
        for chat in chats:
            if chat.author == reciver and chat.reciver == author:
                chat.read = True
                db.session.add(chat)
        db.session.commit()
        if form.validate_on_submit():
            c = Chat(body=form.message.data, author=author, reciver=reciver)
            db.session.add(reciver)
            reciver.unread += 1
            db.session.add(c)
            db.session.add(reciver)
            db.session.commit()
            return redirect(url_for('main.chat', username=username))
        return render_template('chat.html', reciver=reciver, author=author, chats=chats, form=form)

@main.route('/like/<int:id>', methods=['GET', 'POST'])
@login_required
def like(id):
    post = Post.query.get_or_404(id)
    for like in post.likes.all():
        if like.author == current_user:
            flash('你已经赞过了此博客')
            return redirect(url_for('main.post', id=id))

    l = Like(post=post, author=current_user._get_current_object())
    db.session.add(l)
    db.session.commit()
    flash('你赞了博客%s' % post.title)
    return redirect(url_for('main.post', id=id))

@main.route('/favorite/<int:id>/', methods=['GET', 'POST'])
@login_required
def favorite(id):
    post = Post.query.get_or_404(id)
    for favorite in post.favorites.all():
        if favorite.owner == current_user:
            flash('你已经将此博客加入收藏了')
            return redirect(url_for('main.post', id=id))
    
    f = Favorite(post=post, owner=current_user._get_current_object())
    db.session.add(f)
    db.session.commit()
    flash('将博客%s加入到了你的收藏' % post.title)
    return redirect(url_for('main.post', id=id))

@main.route('/user/<username>/favorites/', methods=['GET', 'POST'])
@login_required
def user_favorites(username):
    user = User.query.filter_by(username=username).first()
    if user != current_user:
        abort(403)

    favorites = user.favorites.all()
    return render_template('favorites.html', favorites=favorites, user=user)


@main.route('/blog/uploads/', methods=['GET', 'POST'])
def upload_file():
    form = UploadForm()
    if form.validate_on_submit():
        time = str(datetime.now().year) + str(datetime.now().month) + str(datetime.now().day)
        name = hashlib.md5(time.encode('UTF-8')).hexdigest()[:20]
        filename = photos.save(form.photo.data, name=name+'.')
        file_url = photos.url(filename)
        return redirect('/blog?file=%s' % file_url)
    else:
        file_url = None
    return render_template('upload.html', form=form, file_url=file_url)

@main.route('/change-theme/', methods=['GET', 'POST'])
def change_theme():
    if current_user.dark_theme == True:
        current_user.dark_theme = False
    else:
        current_user.dark_theme = True
    db.session.commit()
    return redirect(url_for('main.index'))

@main.route('/blog/search/')
def search():
    page = int(request.args.get('page', 1))
    keyword = request.args.get('keyword', None)
    pagination = None
    posts = None
    if keyword != None:
        pagination = Post.query.search(keyword).order_by(
            Post.timestamp.desc()).paginate(
            page, per_page=current_app.config['POSTS_PER_PAGE'],
            error_out=False)
        posts = pagination.items
    print(posts)

    return render_template('search.html', posts=posts, keyword=keyword, pagination=pagination)
    