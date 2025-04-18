from django.urls import path
from django.views.generic import TemplateView
from flags.state import flag_enabled
from flags.urls import flagged_paths

import coldfront.core.allocation.views as allocation_views
import coldfront.core.allocation.views_.cluster_access_views as \
    cluster_access_views
import coldfront.core.allocation.views_.secure_dir_views.new_directory.approval_views as secure_dir_new_directory_approval_views
import coldfront.core.allocation.views_.secure_dir_views.user_management.approval_views as secure_dir_user_management_approval_views
import coldfront.core.allocation.views_.secure_dir_views.user_management.request_views as secure_dir_user_management_request_views
import coldfront.core.utils.views.mou_views as mou_views


urlpatterns = [
    path('', allocation_views.AllocationListView.as_view(),
         name='allocation-list'),
    path('project/<int:project_pk>/create',
         allocation_views.AllocationCreateView.as_view(),
         name='allocation-create'),
    path('<int:pk>/',
         allocation_views.AllocationDetailView.as_view(),
         name='allocation-detail'),
    path('<int:pk>/activate-request',
         allocation_views.AllocationActivateRequestView.as_view(),
         name='allocation-activate-request'),
    path('<int:pk>/deny-request',
         allocation_views.AllocationDenyRequestView.as_view(),
         name='allocation-deny-request'),
    path('<int:pk>/add-users',
         allocation_views.AllocationAddUsersView.as_view(),
         name='allocation-add-users'),
    path('<int:pk>/remove-users',
         allocation_views.AllocationRemoveUsersView.as_view(),
         name='allocation-remove-users'),
    path('request-list', allocation_views.AllocationRequestListView.as_view(),
         name='allocation-request-list'),
    # path('<int:pk>/renew', allocation_views.AllocationRenewView.as_view(),
    #      name='allocation-renew'),
    # path('<int:pk>/allocationattribute/add',
    #      allocation_views.AllocationAttributeCreateView.as_view(),
    #      name='allocation-attribute-add'),
    # path('<int:pk>/allocationattribute/delete',
    #      allocation_views.AllocationAttributeDeleteView.as_view(),
    #      name='allocation-attribute-delete'),
    path('allocation-invoice-list',
         allocation_views.AllocationInvoiceListView.as_view(),
         name='allocation-invoice-list'),
    path('<int:pk>/invoice/',
         allocation_views.AllocationInvoiceDetailView.as_view(),
         name='allocation-invoice-detail'),
    path('allocation/<int:pk>/add-invoice-note',
         allocation_views.AllocationAddInvoiceNoteView.as_view(),
         name='allocation-add-invoice-note'),
    path('allocation-invoice-note/<int:pk>/update',
         allocation_views.AllocationUpdateInvoiceNoteView.as_view(),
         name='allocation-update-invoice-note'),
    path('allocation/<int:pk>/invoice/delete/',
         allocation_views.AllocationDeleteInvoiceNoteView.as_view(),
         name='allocation-delete-invoice-note'),
    path('add-allocation-account/',
         allocation_views.AllocationAccountCreateView.as_view(),
         name='add-allocation-account'),
    path('allocation-account-list/',
         allocation_views.AllocationAccountListView.as_view(),
         name='allocation-account-list')]

# Cluster Access Requests
urlpatterns += [
    path('<int:pk>/request-cluster-account/<int:user_pk>',
         cluster_access_views.AllocationRequestClusterAccountView.as_view(),
         name='allocation-request-cluster-account'),
    path('cluster-account/<int:pk>/update-status',
         cluster_access_views.AllocationClusterAccountUpdateStatusView.as_view(),
         name='allocation-cluster-account-update-status'),
    path('cluster-account/<int:pk>/activate-request',
         cluster_access_views.AllocationClusterAccountActivateRequestView.as_view(),
         name='allocation-cluster-account-activate-request'),
    path('cluster-account/<int:pk>/deny-request',
         cluster_access_views.AllocationClusterAccountDenyRequestView.as_view(),
         name='allocation-cluster-account-deny-request'),
    path('cluster-account-request-list',
         cluster_access_views.AllocationClusterAccountRequestListView.as_view(completed=False),
         name='allocation-cluster-account-request-list'),
    path('cluster-account-request-list-completed',
         cluster_access_views.AllocationClusterAccountRequestListView.as_view(completed=True),
         name='allocation-cluster-account-request-list-completed'),
]

with flagged_paths('SECURE_DIRS_REQUESTABLE') as path:
    flagged_url_patterns = [
        # User Management Request Views
        path('<int:pk>/secure-dir-<str:action>-users/',
             secure_dir_user_management_request_views.SecureDirManageUsersView.as_view(),
             name='secure-dir-manage-users'),

        # User Management Approval Views
        path('secure-dir-<str:action>-users-request-list/<str:status>',
             secure_dir_user_management_approval_views.SecureDirManageUsersRequestListView.as_view(),
             name='secure-dir-manage-users-request-list'),
        path('<int:pk>/secure-dir-<str:action>-user-update-status',
             secure_dir_user_management_approval_views.SecureDirManageUsersUpdateStatusView.as_view(),
             name='secure-dir-manage-user-update-status'),
        path('<int:pk>/secure-dir-<str:action>-user-complete-status',
             secure_dir_user_management_approval_views.SecureDirManageUsersCompleteStatusView.as_view(),
             name='secure-dir-manage-user-complete-status'),
        path('<int:pk>/secure-dir-<str:action>-user-deny-request',
             secure_dir_user_management_approval_views.SecureDirManageUsersDenyRequestView.as_view(),
             name='secure-dir-manage-user-deny-request'),

        # New Directory Approval Views
        path('secure-dir-pending-requests/',
             secure_dir_new_directory_approval_views.SecureDirRequestListView.as_view(completed=False),
             name='secure-dir-pending-request-list'),
        path('secure-dir-completed-requests/',
             secure_dir_new_directory_approval_views.SecureDirRequestListView.as_view(completed=True),
             name='secure-dir-completed-request-list'),
        path('secure-dir-request-detail/<int:pk>',
             secure_dir_new_directory_approval_views.SecureDirRequestDetailView.as_view(),
             name='secure-dir-request-detail'),
        path('secure-dir-request/<int:pk>/rdm_consultation',
             secure_dir_new_directory_approval_views.SecureDirRequestReviewRDMConsultView.as_view(),
             name='secure-dir-request-review-rdm-consultation'),
        path('secure-dir-request/<int:pk>/mou',
             secure_dir_new_directory_approval_views.SecureDirRequestReviewMOUView.as_view(),
             name='secure-dir-request-review-mou'),
        path('secure-dir-request/<int:pk>/setup',
             secure_dir_new_directory_approval_views.SecureDirRequestReviewSetupView.as_view(),
             name='secure-dir-request-review-setup'),
        path('secure-dir-request/<int:pk>/deny',
             secure_dir_new_directory_approval_views.SecureDirRequestReviewDenyView.as_view(),
             name='secure-dir-request-review-deny'),
        path('secure-dir-request/<int:pk>/undeny',
             secure_dir_new_directory_approval_views.SecureDirRequestUndenyRequestView.as_view(),
             name='secure-dir-request-undeny'),
        path('secure-dir-request/<int:pk>/download-unsigned-mou/<str:request_type>/',
             mou_views.UnsignedMOUDownloadView.as_view(),
             name='secure-dir-request-download-unsigned-mou'),
        path('secure-dir-request/<int:pk>/upload-mou/<str:request_type>/',
             mou_views.MOUUploadView.as_view(),
             name='secure-dir-request-upload-mou'),
        path('secure-dir-request/<int:pk>/download-mou/<str:request_type>/',
             mou_views.MOUDownloadView.as_view(),
             name='secure-dir-request-download-mou'),
        path('secure-dir-request/<int:pk>/edit-department/',
             secure_dir_new_directory_approval_views.SecureDirRequestEditDepartmentView.as_view(),
             name='secure-dir-request-edit-department'),
        path('secure-dir-request/<int:pk>/notify-pi/',
             secure_dir_new_directory_approval_views.SecureDirRequestNotifyPIView.as_view(),
             name='secure-dir-request-notify-pi'),
    ]

urlpatterns = urlpatterns + flagged_url_patterns
