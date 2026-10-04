# apps/courses/urls.py
"""
Course and lesson URLs that are NOT ViewSets.

Nested paths under a specific course or module live here because DRF's
DefaultRouter can't express them. Everything else (SubjectViewSet,
CourseViewSet) is registered on api/v1/routers.py.

Endpoints declared here:

  GET  /api/v1/courses/{course_slug}/lessons/{identifier}/
       Public lesson viewer. `identifier` accepts slug or UUID.

  POST /api/v1/courses/{course_slug}/modules/
       Admin: create a module under a course.

  GET/PATCH/DELETE /api/v1/courses/{course_slug}/modules/{id}/
       Admin: retrieve/update/delete a module.

  POST /api/v1/modules/{module_id}/lessons/
       Admin: create a lesson under a module.

  GET/PATCH/DELETE /api/v1/modules/{module_id}/lessons/{id}/
       Admin: retrieve/update/delete a lesson.
"""
from django.urls import path

from .views import LessonAdminViewSet, LessonView, ModuleViewSet

app_name = "courses"

urlpatterns = [
    # ── Public lesson viewer ──
    # `identifier` is a slug ("m2l1") or a UUID; the view resolves both.
    path(
        "courses/<slug:course_slug>/lessons/<str:lesson_identifier>/",
        LessonView.as_view(),
        name="lesson",
    ),

    # ── Admin authoring: modules under a course ──
    path(
        "courses/<slug:course_slug>/modules/",
        ModuleViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="course-modules",
    ),
    path(
        "courses/<slug:course_slug>/modules/<uuid:id>/",
        ModuleViewSet.as_view({
            "get": "retrieve",
            "patch": "partial_update",
            "put": "update",
            "delete": "destroy",
        }),
        name="course-module-detail",
    ),

    # ── Admin authoring: lessons under a module ──
    path(
        "modules/<uuid:module_id>/lessons/",
        LessonAdminViewSet.as_view({
            "get": "list",
            "post": "create",
        }),
        name="module-lessons",
    ),
    path(
        "modules/<uuid:module_id>/lessons/<uuid:id>/",
        LessonAdminViewSet.as_view({
            "get": "retrieve",
            "patch": "partial_update",
            "put": "update",
            "delete": "destroy",
        }),
        name="module-lesson-detail",
    ),
]