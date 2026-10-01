"""
Consolidated into views.py.
Wrapper functions delegate dynamically to views.py.
"""

def mentor_classes(request, *args, **kwargs):
    from . import views
    return views.mentor_classes(request, *args, **kwargs)

def api_mentor_classes(request, *args, **kwargs):
    from . import views
    return views.api_mentor_classes(request, *args, **kwargs)

def api_add_class(request, *args, **kwargs):
    from . import views
    return views.api_add_class(request, *args, **kwargs)

def api_mentor_delete_class(request, *args, **kwargs):
    from . import views
    return views.api_mentor_delete_class(request, *args, **kwargs)

def api_mentor_edit_class(request, *args, **kwargs):
    from . import views
    return views.api_mentor_edit_class(request, *args, **kwargs)

def api_student_classes(request, *args, **kwargs):
    from . import views
    return views.api_student_classes(request, *args, **kwargs)

def api_student_tasks(request, *args, **kwargs):
    from . import views
    return views.api_student_tasks(request, *args, **kwargs)
