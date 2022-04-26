from django.urls import path

import coldfront.core.billing.views as billing_views


urlpatterns = [
    path('billable-allocation-list',
         billing_views.BillableAllocationListView.as_view(),
         name='billable-allocation-list'),
    path('is-billing-id-valid/<str:billing_id>/',
         billing_views.IsBillingIDValidView.as_view(),
         name='is-billing-id-valid'),
    path('update-user-billing-ids/',
         billing_views.UpdateUserBillingIDsView.as_view(),
         name='update-user-billing-ids'),
]
