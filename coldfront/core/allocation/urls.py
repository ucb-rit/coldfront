from django.urls import path

import coldfront.core.allocation.views as allocation_views


urlpatterns = [
    path('', allocation_views.AllocationListView.as_view(), name='allocation-list'),
    path('project/<int:project_pk>/create',
         allocation_views.AllocationCreateView.as_view(), name='allocation-create'),
    path('<int:pk>/', allocation_views.AllocationDetailView.as_view(),
         name='allocation-detail'),
    path('<int:pk>/activate-request', allocation_views.AllocationActivateRequestView.as_view(),
         name='allocation-activate-request'),
    path('<int:pk>/deny-request', allocation_views.AllocationDenyRequestView.as_view(),
         name='allocation-deny-request'),
    path('<int:pk>/add-users', allocation_views.AllocationAddUsersView.as_view(),
         name='allocation-add-users'),
    path('<int:pk>/remove-users', allocation_views.AllocationRemoveUsersView.as_view(),
         name='allocation-remove-users'),
    path('<int:pk>/request-cluster-account/<int:user_pk>',
         allocation_views.AllocationRequestClusterAccountView.as_view(),
         name='allocation-request-cluster-account'),
    path('cluster-account/<int:pk>/update-status',
         allocation_views.AllocationClusterAccountUpdateStatusView.as_view(),
         name='allocation-cluster-account-update-status'),
    path('cluster-account/<int:pk>/activate-request',
         allocation_views.AllocationClusterAccountActivateRequestView.as_view(),
         name='allocation-cluster-account-activate-request'),
    path('cluster-account/<int:pk>/deny-request',
         allocation_views.AllocationClusterAccountDenyRequestView.as_view(),
         name='allocation-cluster-account-deny-request'),
    path('request-list', allocation_views.AllocationRequestListView.as_view(),
         name='allocation-request-list'),
    path('cluster-account-request-list',
         allocation_views.AllocationClusterAccountRequestListView.as_view(completed=False),
         name='allocation-cluster-account-request-list'),
    path('cluster-account-request-list-completed',
         allocation_views.AllocationClusterAccountRequestListView.as_view(completed=True),
         name='allocation-cluster-account-request-list-completed'),
    # path('<int:pk>/renew', allocation_views.AllocationRenewView.as_view(),
    #      name='allocation-renew'),
    # path('<int:pk>/allocationattribute/add',
    #      allocation_views.AllocationAttributeCreateView.as_view(), name='allocation-attribute-add'),
    # path('<int:pk>/allocationattribute/delete',
    #      allocation_views.AllocationAttributeDeleteView.as_view(), name='allocation-attribute-delete'),
    path('allocation-invoice-list', allocation_views.AllocationInvoiceListView.as_view(),
         name='allocation-invoice-list'),
    path('<int:pk>/invoice/', allocation_views.AllocationInvoiceDetailView.as_view(),
         name='allocation-invoice-detail'),
    path('allocation/<int:pk>/add-invoice-note',
         allocation_views.AllocationAddInvoiceNoteView.as_view(), name='allocation-add-invoice-note'),
    path('allocation-invoice-note/<int:pk>/update',
         allocation_views.AllocationUpdateInvoiceNoteView.as_view(), name='allocation-update-invoice-note'),
    path('allocation/<int:pk>/invoice/delete/',
         allocation_views.AllocationDeleteInvoiceNoteView.as_view(), name='allocation-delete-invoice-note'),
    path('add-allocation-account/', allocation_views.AllocationAccountCreateView.as_view(),
         name='add-allocation-account'),
    path('allocation-account-list/', allocation_views.AllocationAccountListView.as_view(),
         name='allocation-account-list'),
]


from flags.state import flag_enabled
import coldfront.core.billing.views as billing_views


if flag_enabled('LRC_ONLY'):
    urlpatterns += [
        path('<int:pk>/update-billing-id',
             billing_views.UpdateAllocationBillingIDView.as_view(),
             name='allocation-update-billing-id'),
    ]
