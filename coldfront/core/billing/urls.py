from flags.urls import flagged_paths

import coldfront.core.billing.views as billing_views


with flagged_paths('LRC_ONLY') as f_path:
    urlpatterns = [
        f_path('billable-allocation-list',
               billing_views.BillableAllocationListView.as_view(),
               name='billable-allocation-list'),
        f_path('is-billing-id-valid/<str:billing_id>/',
               billing_views.IsBillingIDValidView.as_view(),
               name='is-billing-id-valid'),
        f_path('update-user-billing-ids/',
               billing_views.UpdateUserBillingIDsView.as_view(),
               name='update-user-billing-ids'),
    ]
