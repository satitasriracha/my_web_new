from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views  # 👈 เพิ่ม
from myapp import views  # 👈 เพิ่มบรรทัดนี้
urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("", include(("myapp.urls", "myapp"), namespace="myapp")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)