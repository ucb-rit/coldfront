from django.urls import path

import coldfront.core.billing.views as billing_views


urlpatterns = [
    path('update-user-billing-ids/',
         billing_views.UpdateUserBillingIDsView.as_view(),
         name='update-user-billing-ids'),
]
