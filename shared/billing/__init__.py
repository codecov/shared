from enum import Enum


class BillingPlan(Enum):
    users_monthly = "users-inappm"
    users_yearly = "users-inappy"
    users_free = "users-free"
    users_basic = "users-basic"
    pr_monthly = "users-pr-inappm"
    pr_yearly = "users-pr-inappy"
    enterprise_cloud_yearly = "users-enterprisey"
    enterprise_cloud_monthly = "users-enterprisem"

    def __init__(self, db_name):
        self.db_name = db_name
