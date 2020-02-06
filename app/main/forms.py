from flask_wtf import FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, ValidationError, SelectField, TextAreaField
from wtforms.validators import *
from .models import *
from flask import flash
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from flask_wtf.file import FileField, FileRequired, FileAllowed
from app import photos

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(1, 64)])

    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')


class RegistrationForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1,64), Email()])

    username = StringField('用户名', validators=[DataRequired(), Length(1,64)])
    password = PasswordField('密码', validators=[DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('密码（重复）', validators=[DataRequired()])
    submit = SubmitField('注册')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            flash('邮箱已注册')
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            flash('用户名已注册')
            raise ValidationError('Username already in use.')


class EditProfileForm(FlaskForm):
    name = StringField('真实姓名', validators=[Length(0,64)])
    location = StringField('地点', validators=[Length(0,64)])
    about_me = TextAreaField('关于我')
    submit = SubmitField('确认')


class EditProfileAdminForm(FlaskForm):
    email = StringField('邮箱', validators=[DataRequired(), Length(1,64), Email()])

    username = StringField('用户名', validators=[DataRequired(), Length(1,64),
                                                   Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                          'Usernames must hav only letters, numbers, dots or underlines')])
    role = SelectField('角色', coerce=int)
    name = StringField('真实姓名', validators=[Length(0,64)])
    location = StringField('地点', validators=[Length(0,64)])
    about_me = TextAreaField('关于我')
    submit = SubmitField('确认')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            flash('邮箱已注册')
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and User.query.filter_by(username=field.data).first():
            flash('用户名已注册')
            raise ValidationError('Username already in use.')

class PostForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired()])
    body = PageDownField("正文", render_kw={'rows':8},validators=[DataRequired()])
    submit = SubmitField('发布', render_kw={'class':'btn btn-info'})

class CommentForm(FlaskForm):
    body = StringField('', validators=[DataRequired()])
    summit = SubmitField('发表评论')


class AdminEditRoleForm(FlaskForm):
    role = SelectField('角色', coerce=int)
    submit = SubmitField('确认')

    def __init__(self, user, *args, **kwargs):
        super(AdminEditRoleForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

class AdminConfirmRemoveForm(FlaskForm):
    password = PasswordField('请输入您的密码以确认', validators=[DataRequired()])
    submit = SubmitField('确认')

class NewsForm(FlaskForm):
    title = StringField('标题', validators=[DataRequired()])
    version = StringField('版本', validators=[DataRequired()])
    body = TextAreaField('正文', render_kw={'rows': 8 ,'cols':2}, validators=[DataRequired()])
    submit = SubmitField('确认')

class CategoryForm(FlaskForm):
    name = StringField('类别名称', validators=[DataRequired()])
    submit = SubmitField('确认')

    def validate_name(self, field):
        if Category.query.filter_by(name=field.data).first():
            flash('类别已存在')
            raise ValidationError('Category already exists.')

class ChatForm(FlaskForm):
    message = TextAreaField('消息', validators=[DataRequired()])
    submit = SubmitField('发送')

class UploadForm(FlaskForm):
    photo = FileField(validators=[
        FileAllowed(photos, '你只能上传图片'), 
        FileRequired('请选择图片')], render_kw={'class':'btn btn-primary'})
    submit = SubmitField('上传')