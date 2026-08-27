from starlette_admin.views import DropDown, Link

from app.admin.views.alert import AlertView
from app.admin.views.contract import ContractView
from app.admin.views.history import ProviderHistoryView
from app.admin.views.home import HomeView
from app.admin.views.provider import ProviderView
from app.admin.views.subscription import SubscriptionView
from app.admin.views.user import UserView
from app.db.models import (
    AlertModel,
    ContractModel,
    ProviderHistoryModel,
    ProviderModel,
    SubscriptionModel,
    UserModel,
)

VIEWS = [
    UserView(UserModel),
    DropDown(
        "Monitoring",
        icon="fa-solid fa-bell",
        always_open=False,
        views=[
            AlertView(AlertModel),
            SubscriptionView(SubscriptionModel),
        ],
    ),
    DropDown(
        "Providers",
        icon="fa-solid fa-server",
        always_open=False,
        views=[
            ProviderView(ProviderModel, menu_label="List"),
            ProviderHistoryView(ProviderHistoryModel, menu_label="History"),
        ],
    ),
    ContractView(ContractModel),
    Link(menu_label="Mini App", icon="fa-solid fa-mobile-screen-button", url="/"),
]

__all__ = ["VIEWS", "HomeView"]
