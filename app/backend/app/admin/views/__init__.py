from starlette_admin.views import DropDown, Link

from app.admin.views.alert import AlertView
from app.admin.views.alert_channel import AlertChannelView
from app.admin.views.bag import BagView
from app.admin.views.bag_slot import BagSlotView
from app.admin.views.history import ProviderHistoryView
from app.admin.views.provider import ProviderView
from app.admin.views.subscription import SubscriptionView
from app.admin.views.user import UserView
from app.db.models import (
    AlertChannelModel,
    AlertModel,
    BagModel,
    BagSlotModel,
    ProviderHistoryModel,
    ProviderModel,
    SubscriptionModel,
    UserModel,
)

VIEWS = [
    Link(menu_label="Home", icon="fa-solid fa-house", url="/admin/"),
    UserView(UserModel),
    DropDown(
        "Monitoring",
        icon="fa-solid fa-bell",
        always_open=False,
        views=[
            AlertView(AlertModel),
            SubscriptionView(SubscriptionModel),
            AlertChannelView(AlertChannelModel),
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
    DropDown(
        "Bags",
        icon="fa-solid fa-cubes",
        always_open=False,
        views=[
            BagView(BagModel, menu_label="List"),
            BagSlotView(BagSlotModel, menu_label="Slots"),
        ],
    ),
    Link(menu_label="App", icon="fa-solid fa-mobile-screen-button", url="/"),
]

__all__ = ["VIEWS"]
