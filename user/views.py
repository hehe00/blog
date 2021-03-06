from django.shortcuts import render, redirect, HttpResponse

from django.db.models import Q
from django.conf import settings
from user.models import *
from django.core.paginator import Paginator  # 用于分页显示
from user.islogin import islogin

from django.http import JsonResponse
from django.http import StreamingHttpResponse
import os
import time
import datetime


# 生成验证码
def yanzhengma(request):
    import random
    str1 = 'ABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0qwertyuiopasdfghjklzxcvbnm'
    rand_str = ''
    for i in range(0, 4):
        rand_str += str1[random.randrange(0, len(str1))]
    request.session['rand_str'] = rand_str
    return JsonResponse({'st': rand_str})


# 登陆
def login(request):
    # 设置关闭浏览器 session 就失效，即关闭浏览器，不管用户是否推出都推出登陆
    request.session.set_expiry(0)

    if request.method == "GET":
        return render(request, 'user/login.html')

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        yzm = request.POST.get('yzm')
        rand_str = request.session.get('rand_str')
        if yzm.upper() != rand_str.upper():
            return render(request, 'user/login.html', {'code': "验证码不正确", 'un': username, "pwd": password})
        if User.objects.filter(username=username, password=password):
            request.session['username'] = username
            username = request.session.get('username')
            user = User.objects.get(username=username)
            request.session['id'] = user.id
            request.session['class_id'] = user.class_id
            request.session['class_num'] = user.class_num
            request.session['school_name'] = user.school_name
            request.session['sign'] = user.sign

            return redirect("/1")

        else:
            if User.objects.filter(username=username):
                return render(request, 'user/login.html', {'ps': "用户名或密码不正确", 'un': username})


# 退出登陆
def logout(request):
    request.session.flush()
    return redirect("/1")


# 注册
def register(request):
    if request.method == 'GET':
        return render(request, 'user/register.html')
    if request.method == 'POST':
        request.session.flush()
        username = request.POST.get('username')
        password = request.POST.get('password', None)
        password2 = request.POST.get('password2', None)
        email = request.POST.get('email')

        resp_data = {"un": username, "em": email}
        if password != password2:
            resp_data["pwd_error"] = "两次密码不一致"
            # return render(request, 'eyizhuce.html')
        if len(password) == 0:
            resp_data["pwd_error"] = "密码不能为空"
        # 验证邮箱是否存在
        if User.objects.filter(email=email):
            resp_data['ema'] = '邮箱已存在'
        if User.objects.filter(username=username):
            resp_data['use'] = '用户名存在'
        if len(resp_data.keys()) > 2:
            return render(request, 'user/register.html', resp_data)

        u1 = User(username=username, password=password, email=email)
        u1.save()
        return render(request, 'user/success.html')


# 验证用户名是否存在
def register_exist(requset):
    uname = requset.GET.get('uname')
    count = User.objects.filter(username=uname).count()
    return JsonResponse({'count': count})


def ucenter(request, pageindex):
    input_page = request.GET.get("input_page")
    if input_page:
        pageindex = int(input_page)

    user_id = request.session.get('id')
    if pageindex == '':
        pageindex = '1'
    list1 = Comment.objects.filter(status=1).order_by('-id')
    paginator = Paginator(list1, 10)

    last_page = len(paginator.page_range)

    if int(pageindex) > last_page:
        pageindex = last_page

    if int(pageindex) <= 0:
        pageindex = 1
    if user_id:
        temp = 'user/shouye_denglu.html'
    else:
        temp = 'user/shouye_dengnolu.html'
    page = paginator.page(int(pageindex))

    username = request.session.get('username')

    return render(request, temp, {'page': page, 'last': last_page, 'username': username})


#  日志
@islogin
def comments(request):
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get('content')
        username = request.session.get('username')
        user_id = request.session.get('id')

        sug1 = Comment(title=title, user_id=user_id, comment=content, user_name=username)
        sug1.save()

        return render(request, 'sug/sug_success.html')


@islogin
def delete_comments(request):
    id = request.GET.get("id")
    page_num = request.GET.get("page")
    user_id = request.session.get('id')

    _comment = Comment.objects.filter(id=id, user_id=user_id, status=1)
    if _comment.exists():
        _comment.update(status=0)
        tk = True
    else:
        tk = False
    list1 = Comment.objects.filter(user_id=user_id, status=1).order_by('-id')

    paginator = Paginator(list1, 9)
    last_page = len(paginator.page_range)
    if int(page_num) > last_page:
        page_num = last_page
    if int(page_num) <= 0:
        page_num = 1

    last_page = len(paginator.page_range)
    page = paginator.page(int(page_num))

    username = request.session.get('username')
    class_num = request.session.get('class_num')
    school_name = request.session.get('school_name')
    sign = request.session.get('sign')
    data = {'page': page, 'last': last_page, 'username': username, 'class_num': class_num,
            'school_name': school_name, 'sign': sign, 'now_page': page_num, "tk": tk}
    return render(request, 'user/user_center.html', data)


# 发起合理化创意
@islogin
def push_sug(request):
    return render(request, 'user/youhua.html')


def load(request):
    name = request.GET.get("ld")

    path = settings.MEDIA_ROOT + name

    def file_iterator(file_path, chunk_size=512):
        """
        文件生成器,防止文件过大，导致内存溢出
        :param file_path: 文件绝对路径
        :param chunk_size: 块大小
        :return: 生成器
        """
        with open(file_path, mode='rb') as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    try:

        response = StreamingHttpResponse(file_iterator(path))

        response['Content-Type'] = 'application/octet-stream'

        response['Content-Disposition'] = 'attachment;filename="{}"'.format(name)
    except:
        return HttpResponse("Sorry but Not Found the File")

    return response


# 修改密码
def xgmm(request):
    if request.method == 'GET':
        return render(request, 'user/xgmm.html')
    if request.method == "POST":
        old_pwd = request.POST.get('pwd')
        pwd = request.POST.get('newpwd')
        id = request.session.get('id')
        user = User.objects.filter(id=id, password=old_pwd)
        if not user.exists():
            return render(request, 'user/xgmm_cg.html', {"status": 0, "msg": "原密码不正确，请重新输入"})
        user.update(password=pwd)
        request.session.flush()

        return render(request, 'user/xgmm_cg.html', {"status": 1, "msg": "原密码不正确，请重新输入"})


@islogin
def photo(request, pageindex):
    input_page = request.GET.get("input_page")
    if input_page:
        pageindex = int(input_page)

    user_id = request.session.get('id')
    if pageindex == '':
        pageindex = '1'

    list1 = Photo.objects.filter(user_id=user_id, status=1).filter(Q(class_id="")).order_by('-id')

    paginator = Paginator(list1, 9)

    last_page = len(paginator.page_range)

    if int(pageindex) > last_page:
        pageindex = last_page
    if int(pageindex) <= 0:
        pageindex = 1
    page = paginator.page(int(pageindex))

    return render(request, 'user/psersion_photo.html',
                  {'page': page, 'now_page': pageindex, 'last': last_page, 'sign': "认识你真好"})


# 上传图片
@islogin
def upload(request):
    user_id = request.session.get('id')
    username = request.session.get('username')
    fls = request.FILES.values()
    status = -1
    msg = "请选择上传的照片！"
    for f1 in fls:
        status = 1
        msg = "图片上传成功"

        houzhui = f1.name.split('.')[1]

        fn = "{id}-{_time}.{hz}".format(id=user_id, _time=str(int(time.time())), hz=houzhui)
        fname = os.path.join(settings.MEDIA_ROOT, fn)
        with open(fname, 'wb') as f:
            for c in f1.chunks():
                f.write(c)
        Photo.objects.create(user_id=user_id, img=fn, user_name=username)

    return JsonResponse({"status": status, "msg": msg})


# 删除图片
@islogin
def delete_photo(request):
    id = request.GET.get("id")
    page_num = request.GET.get("page")
    user_id = request.session.get('id')

    Photo.objects.filter(id=id).update(status=0)
    list1 = Photo.objects.filter(user_id=user_id, status=1).order_by('-id')
    paginator = Paginator(list1, 9)
    last_page = len(paginator.page_range)
    if int(page_num) > last_page:
        page_num = last_page
    if int(page_num) <= 0:
        page_num = 1
    last_page = len(paginator.page_range)
    page = paginator.page(int(page_num))

    return render(request, 'user/psersion_photo.html',
                  {'page': page, 'now_page': page_num, 'last': last_page, 'sign': "认识你真好", "tk": True})


@islogin
def school_photo(request, pageindex):
    input_page = request.GET.get("input_page")
    if input_page:
        pageindex = int(input_page)

    class_id = request.session.get('class_id')
    if not class_id:
        return render(request, 'user/class_photo.html',
                      {'now_page': pageindex, 'last': 1, 'sign': "认识你真好"})
    if pageindex == '':
        pageindex = '1'

    list1 = Photo.objects.filter(class_id=class_id, status=1).order_by('-id')

    paginator = Paginator(list1, 9)

    last_page = len(paginator.page_range)

    if int(pageindex) > last_page:
        pageindex = last_page
    if int(pageindex) <= 0:
        pageindex = 1
    page = paginator.page(int(pageindex))

    return render(request, 'user/class_photo.html',
                  {'page': page, 'now_page': pageindex, 'last': last_page, 'sign': "认识你真好"})


# 上传图片
@islogin
def class_upload(request):
    user_id = request.session.get('id')
    username = request.session.get('username')
    class_id = request.session.get('class_id')
    if not ClassInfo.objects.filter(id=class_id).exists():
        return JsonResponse({"status": 0, "msg": "请联系管理员绑定班级！"})

    fls = request.FILES.values()
    status = -1
    msg = "请选择上传的照片！"
    for f1 in fls:
        status = 1
        msg = "图片上传成功"

        houzhui = f1.name.split('.')[1]

        fn = "{id}-{_class}-{_time}.{hz}".format(id=user_id, _class=class_id, _time=str(int(time.time())), hz=houzhui)
        fname = os.path.join(settings.MEDIA_ROOT, fn)
        with open(fname, 'wb') as f:
            for c in f1.chunks():
                f.write(c)
        Photo.objects.create(user_id=user_id, user_name=username, class_id=class_id, img=fn)

    return JsonResponse({"status": status, "msg": msg})


# 删除图片
@islogin
def delete_class_photo(request):
    id = request.GET.get("id")
    page_num = request.GET.get("page")
    class_id = request.session.get('class_id')

    Photo.objects.filter(id=id, class_id=class_id).update(status=0)
    list1 = Photo.objects.filter(class_id=class_id, status=1).order_by('-id')

    paginator = Paginator(list1, 9)
    last_page = len(paginator.page_range)
    if int(page_num) > last_page:
        page_num = last_page
    if int(page_num) <= 0:
        page_num = 1
    last_page = len(paginator.page_range)
    page = paginator.page(int(page_num))

    return render(request, 'user/class_photo.html',
                  {'page': page, 'now_page': page_num, 'last': last_page, 'sign': "认识你真好", "tk": True})


@islogin
def user_center(request, pageindex):
    input_page = request.GET.get("input_page")
    if input_page:
        pageindex = int(input_page)

    user_id = request.session.get('id')
    if pageindex == '':
        pageindex = '1'
    list1 = Comment.objects.filter(user_id=user_id, status=1).order_by('-id')
    paginator = Paginator(list1, 10)

    last_page = len(paginator.page_range)

    if int(pageindex) > last_page:
        pageindex = last_page

    if int(pageindex) <= 0:
        pageindex = 1

    page = paginator.page(int(pageindex))

    username = request.session.get('username')
    class_num = request.session.get('class_num')
    school_name = request.session.get('school_name')
    sign = request.session.get('sign')

    return render(request, 'user/user_center.html',
                  {'page': page, 'last': last_page, 'username': username, 'class_num': class_num,
                   'school_name': school_name, 'sign': sign, 'now_page': pageindex})


def update_sign(request):
    if request.method == 'GET':
        return render(request, 'user/update_sign.html')
    if request.method == "POST":
        sign = request.POST.get('sign')
        id = request.session.get('id')
        User.objects.filter(id=id).update(sign=sign)
        username = request.session.get('username')
        user_id = request.session.get('id')
        class_num = request.session.get('class_num')
        school_name = request.session.get('school_name')
        request.session['sign'] = sign
        list1 = Comment.objects.filter(user_id=user_id, status=1).order_by('-id')
        paginator = Paginator(list1, 10)
        page = paginator.page(int(1))
        return render(request, 'user/user_center.html',
                      {'page': page, "status": 1, "msg": "原密码不正确，请重新输入", 'username': username, 'class_num': class_num,
                       'school_name': school_name, 'sign': sign})


@islogin
def school_conment(request, pageindex):
    input_page = request.GET.get("input_page")
    if input_page:
        pageindex = int(input_page)

    class_id = request.session.get('class_id')
    if pageindex == '':
        pageindex = '1'
    list1 = SchoolComment.objects.filter(status=1, class_id=class_id).order_by('-id')
    paginator = Paginator(list1, 10)

    last_page = len(paginator.page_range)

    if int(pageindex) > last_page:
        pageindex = last_page

    if int(pageindex) <= 0:
        pageindex = 1

    page = paginator.page(int(pageindex))

    username = request.session.get('username')
    class_num = request.session.get('class_num')
    school_name = request.session.get('school_name')
    sign = request.session.get('sign')
    _List = []
    for each in page:
        create = datetime.datetime.strptime(str(each.create_date)[:19], "%Y-%m-%d %H:%M:%S")
        _List.append({
            "id": each.id,
            "user_name": each.user_name,
            "comments": each.comment,
            "create_date": str(create + datetime.timedelta(hours=8))
        })
    return render(request, 'user/index.html',
                  {'page': page, 'last': last_page, 'username': username, 'class_num': class_num,
                   'school_name': school_name, 'sign': sign, "data": _List})


def update_school_comment(request):
    if request.method == 'GET':
        return render(request, 'user/index.html')
    if request.method == "POST":
        comment = request.POST.get('comment')

        username = request.session.get('username')
        user_id = request.session.get('id')
        class_id = request.session.get('class_id')
        if ClassInfo.objects.filter(id=class_id).exists():
            status = 1

            SchoolComment.objects.create(user_id=user_id, class_id=class_id, comment=comment, user_name=username)
        else:
            status = 0
        return JsonResponse({"status": status})


@islogin
def query_first(request):
    if request.method == 'GET':
        return render(request, "user/query.html", {})


@islogin
def query(request, pageindex):
    if request.method == 'GET':

        input_page = request.GET.get("input_page")
        if input_page:
            pageindex = int(input_page)

        user_id = request.session.get('id')
        class_id = request.session.get('class_id')
        if pageindex == '':
            pageindex = '1'
        list1 = SchoolComment.objects.filter(user_id=user_id, status=1, class_id=class_id).order_by('-id')
        paginator = Paginator(list1, 10)

        last_page = len(paginator.page_range)

        if int(pageindex) > last_page:
            pageindex = last_page

        if int(pageindex) <= 0:
            pageindex = 1

        page = paginator.page(int(pageindex))

        username = request.session.get('username')
        class_num = request.session.get('class_num')
        school_name = request.session.get('school_name')
        sign = request.session.get('sign')
        _List = []
        for each in page:
            create = datetime.datetime.strptime(str(each.create_date)[:19], "%Y-%m-%d %H:%M:%S")
            _List.append({
                "id": each.id,
                "user_name": each.user_name,
                "comments": each.comment,
                "create_date": str(create + datetime.timedelta(hours=8))
            })
        return render(request, 'user/index.html',
                      {'page': page, 'last': last_page, 'username': username, 'class_num': class_num,
                       'school_name': school_name, 'sign': sign, "data": _List})

    else:
        data = request.POST

        query_type = data.get("query_type")
        query_value = data.get("query_value")
        request.session['query_type'] = query_type
        request.session['query_value'] = query_value
        if query_type == "学校":
            school = School.objects.filter(school_name=query_value)
            if school.exists():
                school_name = school.first().school_name
                comment = school.first().comment
                status = 1
            else:
                school_name = ""
                comment = ""
                status = 0

            return render(request, 'user/query.html',
                          {"school_name": school_name, "comment": comment, "status": status, "query_type": query_type})
        elif query_type == "班级":
            _class = ClassInfo.objects.filter(class_name=query_value)
            if _class.exists():
                school_name = _class.first().school_name
                class_name = _class.first().class_name
                status = 1
                students_num = User.objects.filter(class_num=class_name).count()
            else:
                school_name = ""
                class_name = ""
                status = 0
                students_num = 0

            return render(request, 'user/query.html',
                          {"school_name": school_name, "class_name": class_name, "status": status,
                           "query_type": query_type, "students_num": students_num})
        else:
            # 同学
            class_id = request.session['class_id']
            user = User.objects.filter(class_id=class_id, username=query_value)
            if user.exists():
                username = user.first().username
                email = user.first().email
                class_name = user.first().class_num
                school_name = user.first().school_name
                sign = user.first().sign
                status = 1
            else:
                username = ""
                email = ""
                class_name = ""
                school_name = ""
                sign = ""
                status = 0

            return render(request, 'user/query.html',
                          {"email": email, "class_name": class_name, "status": status, "query_type": query_type,
                           "username": username, "sign": sign, "school_name": school_name})
